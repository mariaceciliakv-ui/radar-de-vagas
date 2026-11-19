"""Script principal de execução do RADAR DE VAGAS — Integração completa com planilha Excel.

Fluxo de cada execução:
  1. Lê vagas já existentes na planilha (preserva histórico).
  2. Busca novas vagas em LinkedIn, Indeed, Glassdoor e Gupy.
  3. Elimina duplicatas (cruzando banco SQLite + planilha).
  4. Calcula aderência (Fit Score 0–100) de cada vaga nova.
  5. Classifica prioridade e registra data da busca.
  6. Insere somente vagas novas — preserva dados existentes.
  7. Exibe relatório consolidado pós-execução.

USO:
    python run_radar.py                  # Execução padrão
    python run_radar.py --reset-db       # Limpa banco SQLite antes de executar (vê vagas já vistas)
    python run_radar.py --max-queries 8  # Amplia número de termos buscados
    python run_radar.py --limit 30       # Resultados máximos por query
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List

# ── Encoding UTF-8 no Windows ────────────────────────────────────────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from agents.harvester import JobHarvesterAgent
from src.exporters.excel_exporter import ExcelExporter
from src.core.database import DatabaseManager
from src.core.deduplication import DeduplicationEngine
from src.core.scorer import FitScorer
from src.core.models import JobOpportunity
import yaml

logging.basicConfig(
    level=logging.WARNING,   # Silencia logs de bibliotecas externas
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RadarDeVagas.Main")
logging.getLogger("RadarDeVagas").setLevel(logging.INFO)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sep(char="─", w=76):
    print(char * w)


def _load_yaml(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _print_header():
    _sep("═")
    print("  🛰️  RADAR DE VAGAS — EXECUÇÃO INTEGRADA COM PLANILHA")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}")
    _sep("═")
    print()


def _print_report(stats: Dict[str, Any]):
    print()
    _sep("═")
    print("  📊  RELATÓRIO PÓS-EXECUÇÃO")
    _sep("═")
    print(f"  🔎 Vagas encontradas nesta busca       : {stats['total_encontradas']}")
    print(f"  ✅ Novas vagas inseridas na planilha   : {stats['novas_inseridas']}")
    print(f"  🗑️  Vagas descartadas (dupl./filtros)  : {stats['total_descartadas']}")
    _sep()
    print(f"  🌐 Remotas (novas / total planilha)    : {stats['novas_remotas']} / {stats['total_remotas']}")
    print(f"  🏠 Híbridas (novas / total planilha)   : {stats['novas_hibridas']} / {stats['total_hibridas']}")
    print(f"  ⭐ Score ≥ 80% (novas / total planilha): {stats['novas_score_80']} / {stats['total_score_80']}")
    _sep()
    print(f"  📁 Total na planilha                   : {stats['total_geral_planilha']} vagas")
    print(f"  📂 Arquivo                             : {os.path.abspath(stats['arquivo_planilha'])}")
    _sep("═")
    print()


# ── Pipeline principal ─────────────────────────────────────────────────────────

def execute_radar_sync(
    max_queries: int = 8,
    limit_results: int = 20,
    reset_db: bool = False
) -> Dict[str, Any]:

    _print_header()

    # ── Carregar configurações ────────────────────────────────────────────────
    cargos_cfg   = _load_yaml("config/cargos.yaml")
    search_cfg   = _load_yaml("config/search_queries.yaml")

    exporter = ExcelExporter()
    db       = DatabaseManager()

    # ── 0. Reset opcional do banco SQLite ─────────────────────────────────────
    if reset_db:
        db_path = os.path.join("data", "job_vault.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            print("🔄 Banco SQLite resetado — vagas anteriores serão reavaliadas.\n")
        db = DatabaseManager()   # Reinicializa com banco vazio

    # ── 1. Ler vagas já existentes na planilha ────────────────────────────────
    existing_sheet_jobs = exporter.read_existing_jobs()
    print(f"📖 Vagas já registradas na planilha  : {len(existing_sheet_jobs)}")

    # ── 2. Montar queries de busca ────────────────────────────────────────────
    alta    = cargos_cfg.get("prioridade_alta", [])
    media   = cargos_cfg.get("prioridade_media", [])
    # Intercalar alta e média para distribuir bem as buscas
    search_terms: List[str] = []
    for a, m in zip(alta, media):
        search_terms.extend([a, m])
    # Completar com sobras
    search_terms += alta[len(media):]
    search_terms += media[len(alta):]
    search_terms = search_terms[:max_queries]

    locations = ["Campinas, SP", "Remoto", "Brasil"]

    print(f"🔎 Termos de busca ({len(search_terms)})              : {', '.join(search_terms)}")
    print(f"📍 Localidades                        : {', '.join(locations)}")
    print()

    # ── 3. Coleta de vagas ────────────────────────────────────────────────────
    print("⏳ Iniciando coleta nas fontes (LinkedIn, Indeed, Glassdoor, Gupy)...")
    harvester = JobHarvesterAgent(search_cfg)
    raw_jobs = harvester.search_all_sources(
        queries=search_terms,
        locations=locations,
        max_results_per_query=limit_results
    )
    total_encontradas = len(raw_jobs)
    print(f"📦 Vagas brutas coletadas             : {total_encontradas}")

    if not raw_jobs:
        print("\n⚠  Nenhuma vaga coletada. Verifique conexão ou tente novamente.")
        return {"total_encontradas": 0, "novas_inseridas": 0, "total_descartadas": 0,
                "novas_remotas": 0, "novas_hibridas": 0, "novas_score_80": 0,
                "total_remotas": 0, "total_hibridas": 0, "total_score_80": 0,
                "total_geral_planilha": len(existing_sheet_jobs),
                "arquivo_planilha": exporter.default_file}

    # ── 4. Deduplicação (SQLite + Planilha) ───────────────────────────────────
    seen_hashes = db.get_all_seen_hashes()
    # Adicionar hashes da planilha existente ao conjunto
    for ej in existing_sheet_jobs:
        h = ej.id or DeduplicationEngine.generate_job_hash(
            ej.empresa, ej.titulo, ej.localizacao, ej.url
        )
        seen_hashes.add(h)

    unique_candidates: List[JobOpportunity] = []
    descartadas_dup = 0

    for job in raw_jobs:
        if not job.id:
            job.id = DeduplicationEngine.generate_job_hash(
                job.empresa, job.titulo, job.localizacao, job.url
            )
        if job.id not in seen_hashes:
            seen_hashes.add(job.id)
            unique_candidates.append(job)
        else:
            descartadas_dup += 1

    print(f"🔁 Duplicatas eliminadas              : {descartadas_dup}")
    print(f"🆕 Candidatas únicas para avaliação   : {len(unique_candidates)}")

    # ── 5. Calcular Fit Score e Classificar ───────────────────────────────────
    new_scored_jobs: List[JobOpportunity] = []
    descartadas_filtro = 0

    for job in unique_candidates:
        result = FitScorer.evaluate_job(job)
        if result.score_total > 0:
            new_scored_jobs.append(job)
        else:
            descartadas_filtro += 1

    # Ordenar por score decrescente
    new_scored_jobs.sort(key=lambda j: j.score, reverse=True)

    total_descartadas = descartadas_dup + descartadas_filtro
    print(f"🚫 Descartadas por filtro negativo    : {descartadas_filtro}")
    print(f"✅ Vagas qualificadas para inserção   : {len(new_scored_jobs)}")
    print()

    # ── 6. Persistir no banco SQLite ──────────────────────────────────────────
    if new_scored_jobs:
        db.save_jobs_batch(new_scored_jobs)

    # ── 7. Sincronizar com planilha Excel ─────────────────────────────────────
    print("💾 Sincronizando com planilha Excel...")
    total_na_planilha, novas_inseridas, file_path = exporter.sync_and_save(new_scored_jobs)
    print(f"   ↳ {novas_inseridas} vaga(s) nova(s) inserida(s). Total: {total_na_planilha}.")
    # Collect recruiters for newly inserted jobs and sync them
    from agents.recruiter_collector import collect_recruiters
    recruiters = []
    for job in new_scored_jobs:
        recruiters.extend(collect_recruiters(job))
    if recruiters:
        exporter.sync_recruiters(recruiters, file_path)

    # ── 8. Métricas consolidadas ──────────────────────────────────────────────
    all_sheet_jobs  = exporter.read_existing_jobs(file_path)
    total_remotas   = sum(1 for j in all_sheet_jobs if j.modalidade == "Remoto")
    total_hibridas  = sum(1 for j in all_sheet_jobs if j.modalidade == "Híbrido")
    total_score_80  = sum(1 for j in all_sheet_jobs if j.score >= 80.0)

    novas_remotas   = sum(1 for j in new_scored_jobs if j.modalidade == "Remoto")
    novas_hibridas  = sum(1 for j in new_scored_jobs if j.modalidade == "Híbrido")
    novas_score_80  = sum(1 for j in new_scored_jobs if j.score >= 80.0)

    stats = {
        "total_encontradas":  total_encontradas,
        "novas_inseridas":    novas_inseridas,
        "total_descartadas":  total_descartadas,
        "novas_remotas":      novas_remotas,
        "novas_hibridas":     novas_hibridas,
        "novas_score_80":     novas_score_80,
        "total_remotas":      total_remotas,
        "total_hibridas":     total_hibridas,
        "total_score_80":     total_score_80,
        "total_geral_planilha": total_na_planilha,
        "arquivo_planilha":   file_path
    }

    # ── 9. Preview das novas vagas inseridas ──────────────────────────────────
    if new_scored_jobs:
        print()
        _sep()
        print(f"  {'Score':<7} {'Prioridade':<22} {'Cargo':<32} {'Empresa':<20} {'Modal.'}")
        _sep()
        for job in new_scored_jobs[:15]:  # Exibir até 15
            score_str = f"{job.score:.0f}%"
            prior     = job.classificacao[:20]
            cargo     = job.titulo[:30]
            empresa   = job.empresa[:18]
            modal     = job.modalidade
            icon = "⭐" if job.score >= 80 else ("✅" if job.score >= 65 else "🔵")
            print(f"  {icon} {score_str:<6} {prior:<22} {cargo:<32} {empresa:<20} {modal}")
        if len(new_scored_jobs) > 15:
            print(f"  ... e mais {len(new_scored_jobs) - 15} vaga(s). Consulte a planilha.")
        _sep()

    _print_report(stats)

    # ── 10. Atualizar Dashboard Web (GitHub Pages) ──────────────────────────
    try:
        from export_web_dashboard import export_dashboard
        export_dashboard(excel_path=file_path)
    except Exception as e:
        logger.debug(f"Aviso ao exportar dashboard web: {e}")

    return stats


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Radar de Vagas — Pipeline integrado com planilha")
    parser.add_argument("--reset-db", action="store_true",
                        help="Apaga o banco SQLite antes de executar (reavalia vagas já vistas).")
    parser.add_argument("--max-queries", type=int, default=8,
                        help="Número máximo de termos de busca (padrão: 8).")
    parser.add_argument("--limit", type=int, default=20,
                        help="Resultados por query por fonte (padrão: 20).")
    args = parser.parse_args()

    execute_radar_sync(
        max_queries=args.max_queries,
        limit_results=args.limit,
        reset_db=args.reset_db
    )

"""Script dedicado ao Agente de Recrutadores — Radar de Vagas.

Execução isolada do mapeamento de recrutadores:
  1. Lê vagas da planilha com score >= 65% (configurável).
  2. Pesquisa recrutadores via Google X-Ray Search (perfis LinkedIn públicos).
  3. Exibe os resultados para validação.
  4. Solicita confirmação antes de gravar na planilha.

USO:
    python run_recruiters.py [--dry-run] [--min-score 70]
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.exporters.excel_exporter import ExcelExporter
from agents.recruiter_hunter import RecruiterHunterAgent

# ── Configurações ────────────────────────────────────────────────────────────
DEFAULT_OUTPUT_DIR = "data/output"
DEFAULT_XLSX = os.path.join(DEFAULT_OUTPUT_DIR, "Radar_Vagas_Data.xlsx")
DEFAULT_MIN_SCORE = 65.0  # Conforme scoring_rules.yaml


# ── Helpers ──────────────────────────────────────────────────────────────────

def print_separator(char="─", width=72):
    print(char * width)


def print_header():
    print_separator("═")
    print("  🛰️  RADAR DE VAGAS — AGENTE DE RECRUTADORES")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print_separator("═")
    print()


def load_qualified_jobs(xlsx_path: str, min_score: float) -> list:
    """Lê vagas da planilha que atendem o limiar de score."""
    exporter = ExcelExporter()
    all_jobs = exporter.read_existing_jobs(xlsx_path)

    qualified = [
        job for job in all_jobs
        if job.score >= min_score
    ]
    return all_jobs, qualified


def build_company_list(qualified_jobs: list) -> list:
    """Deduplica empresas e monta lista de dicts para o agente."""
    seen = set()
    companies = []
    for job in qualified_jobs:
        key = job.empresa.lower().strip()
        if key and key not in seen:
            seen.add(key)
            companies.append({
                "empresa": job.empresa.strip(),
                "vaga_relacionada": job.titulo.strip(),
            })
    return companies


def display_results(recruiters: list) -> None:
    """Exibe os recrutadores encontrados de forma legível."""
    if not recruiters:
        print("\n⚠  Nenhum recrutador encontrado com os critérios atuais.")
        print("   Dica: Empresas muito novas ou pequenas podem não ter perfis indexados.")
        return

    print(f"\n✅  {len(recruiters)} contato(s) mapeado(s):\n")
    print_separator()
    print(f"  {'#':<4} {'Empresa':<24} {'Nome':<22} {'Cargo':<28} {'Prior.':<8} {'Link'}")
    print_separator()

    for i, rec in enumerate(recruiters, 1):
        nome = rec.get("nome", "—")[:20]
        empresa = rec.get("empresa", "—")[:22]
        cargo = rec.get("cargo", "—")[:26]
        prior = rec.get("prioridade", "—")
        url = rec.get("linkedin_url", "—")

        prior_icon = "🟢" if prior == "Alta" else "🟡"
        url_display = url[:45] + "..." if url and len(url) > 48 else (url or "—")

        print(f"  {i:<4} {empresa:<24} {nome:<22} {cargo:<28} {prior_icon} {prior:<6} {url_display}")

    print_separator()


def save_dry_run_json(recruiters: list) -> str:
    """Salva os resultados em JSON para revisão sem gravar na planilha."""
    os.makedirs("data", exist_ok=True)
    path = "data/dry_run_recruiters.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(recruiters, f, ensure_ascii=False, indent=2)
    return path


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Agente de Recrutadores — Radar de Vagas")
    parser.add_argument("--dry-run", action="store_true",
                        help="Executa sem gravar na planilha (apenas exibe e salva JSON).")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Grava automaticamente na planilha sem solicitar confirmação interativa.")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        help=f"Score mínimo das vagas para ativar a busca (padrão: {DEFAULT_MIN_SCORE}).")
    parser.add_argument("--xlsx", type=str, default=DEFAULT_XLSX,
                        help="Caminho da planilha Excel.")
    args = parser.parse_args()

    print_header()

    # ── 1. Carregar vagas qualificadas ────────────────────────────────────────
    print(f"📂 Lendo vagas da planilha: {args.xlsx}")
    if not os.path.exists(args.xlsx):
        print(f"\n❌ Planilha não encontrada: {args.xlsx}")
        print("   Execute primeiro: python run_radar.py")
        sys.exit(1)

    all_jobs, qualified_jobs = load_qualified_jobs(args.xlsx, args.min_score)
    companies = build_company_list(qualified_jobs)

    print(f"   Total de vagas na planilha : {len(all_jobs)}")
    print(f"   Vagas com score ≥ {args.min_score:.0f}%    : {len(qualified_jobs)}")
    print(f"   Empresas únicas para busca : {len(companies)}")

    if not companies:
        print(f"\n⚠  Nenhuma vaga com score ≥ {args.min_score:.0f}% encontrada.")
        print("   Dica: Rode 'python run_radar.py' para popular a planilha,")
        print("         ou use '--min-score 40' para abaixar o limiar temporariamente.")
        sys.exit(0)

    print("\n📋 Empresas que serão pesquisadas:")
    for i, c in enumerate(companies, 1):
        print(f"   {i}. {c['empresa']} → vaga: {c['vaga_relacionada'][:50]}")

    print()
    print_separator()
    print()

    # ── 2. Executar Agente de Recrutadores ────────────────────────────────────
    print("🔍 Iniciando pesquisa de recrutadores via Google X-Ray Search...")
    print("   (Apenas perfis LinkedIn publicamente disponíveis)\n")

    agent = RecruiterHunterAgent(min_score_threshold=args.min_score)
    recruiters = agent.find_recruiters_for_companies(companies)

    # ── 3. Exibir resultados ──────────────────────────────────────────────────
    display_results(recruiters)

    # ── 4. Dry-run: salvar JSON sem gravar na planilha ────────────────────────
    if args.dry_run:
        json_path = save_dry_run_json(recruiters)
        print(f"\n📄 Modo DRY-RUN — Resultados salvos em: {json_path}")
        print("   Nenhuma alteração foi feita na planilha.")
        return

    # ── 5. Confirmação antes de gravar ────────────────────────────────────────
    if not recruiters:
        print("\nNada a gravar. Encerrando.")
        return

    if args.yes:
        resposta = "s"
    else:
        print("\n⚡ Deseja gravar estes recrutadores na planilha? [s/N]: ", end="")
        try:
            resposta = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            resposta = "n"

    if resposta not in ("s", "sim", "y", "yes"):
        json_path = save_dry_run_json(recruiters)
        print(f"\n⏭  Gravação cancelada. Resultados salvos em: {json_path}")
        return

    # ── 6. Gravar na planilha ─────────────────────────────────────────────────
    print("\n💾 Gravando na planilha...")
    exporter = ExcelExporter()
    total, novos, xlsx_path = exporter.sync_recruiters(recruiters, args.xlsx)

    print_separator("═")
    print("  📊 RELATÓRIO — AGENTE DE RECRUTADORES")
    print_separator("═")
    print(f"  Contatos encontrados    : {len(recruiters)}")
    print(f"  Novos inseridos         : {novos}")
    print(f"  Já existiam na planilha : {len(recruiters) - novos}")
    print(f"  Total na aba Recrutadores: {total}")
    print(f"  Planilha salva em       : {xlsx_path}")
    print_separator("═")
    print()
    print("✅ Concluído! Abra a aba '👥 Recrutadores' na planilha para revisar.")
    print()


if __name__ == "__main__":
    main()

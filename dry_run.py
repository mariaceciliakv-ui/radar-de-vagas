"""Execução de validação do Agente de Vagas (Dry Run: no máximo 20 vagas, sem gravação na planilha)."""

import sys
import os
import json
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath("."))

from agents.harvester import JobHarvesterAgent
from src.core.scorer import FitScorer
from src.core.deduplication import DeduplicationEngine
from src.core.models import JobOpportunity

# Garantir codificação UTF-8 no stdout/stderr no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def run_dry_search(max_jobs: int = 20):
    print("\n" + "="*80)
    print("🛰️  RADAR DE VAGAS — EXECUÇÃO DE VALIDAÇÃO (DRY RUN)")
    print(f"🎯 Limite máximo: {max_jobs} vagas | Gravação em planilha: DESATIVADA")
    print("="*80 + "\n")

    harvester = JobHarvesterAgent()

    # Termos prioritários de busca alinhados com o perfil
    queries = [
        "Analista de BI Jr",
        "Analista de Dados Jr",
        "Power BI",
        "Analista de Indicadores",
        "Analista de Operações"
    ]
    locations = ["Campinas, SP", "Remoto", "Brasil"]

    print(f"🔎 Realizando busca nas fontes públicas para os termos: {queries}...")
    raw_jobs = harvester.search_all_sources(queries, locations, max_results_per_query=8)

    print(f"📦 Total bruto de vagas capturadas: {len(raw_jobs)}")

    # Deduplicação
    seen_hashes = set()
    unique_jobs = []
    for job in raw_jobs:
        if not job.id:
            job.id = DeduplicationEngine.generate_job_hash(job.empresa, job.titulo, job.localizacao, job.url)
        if job.id not in seen_hashes:
            seen_hashes.add(job.id)
            unique_jobs.append(job)

    print(f"✨ Vagas únicas após deduplicação: {len(unique_jobs)}")

    # Cálculo do Fit Score para cada vaga
    scored_jobs = []
    for job in unique_jobs:
        res = FitScorer.evaluate_job(job)
        if res.score_total > 0: # Não descartadas por termos negativos
            scored_jobs.append(job)

    # Ordenar por maior pontuação (Top Score)
    scored_jobs.sort(key=lambda x: x.score, reverse=True)
    selected_jobs = scored_jobs[:max_jobs]

    print(f"\n📊 TOP {len(selected_jobs)} OPORTUNIDADES RANQUEADAS:")
    print("="*80)

    for idx, job in enumerate(selected_jobs, 1):
        print(f"\n🏆 #{idx} | Score: {job.score:.1f}% — [{job.classificacao}]")
        print(f"   📌 Cargo:       {job.titulo}")
        print(f"   🏢 Empresa:     {job.empresa}")
        print(f"   📍 Localização: {job.localizacao} | Modalidade: {job.modalidade}")
        print(f"   💰 Salário:     {job.salario} | Publicada: {job.data_publicacao}")
        print(f"   🛠️  Skills:      {', '.join(job.pontos_fortes) if job.pontos_fortes else 'Gerais / Negócios'}")
        print(f"   📈 Desenv.:     {', '.join(job.oportunidades_desenvolvimento) if job.oportunidades_desenvolvimento else 'N/A'}")
        print(f"   🌐 Link:        {job.url}")
        print(f"   🏷️  Fonte:       {job.fonte}")
        print("-" * 80)

    # Salvar resultado estruturado temporário em JSON no scratch para exibição segura
    results_payload = [
        {
            "rank": idx,
            "score": f"{job.score:.1f}%",
            "classificacao": job.classificacao,
            "cargo": job.titulo,
            "empresa": job.empresa,
            "localizacao": job.localizacao,
            "modalidade": job.modalidade,
            "salario": job.salario,
            "data_publicacao": job.data_publicacao,
            "skills": job.pontos_fortes,
            "oportunidades_desenvolvimento": job.oportunidades_desenvolvimento,
            "url": job.url,
            "fonte": job.fonte
        }
        for idx, job in enumerate(selected_jobs, 1)
    ]

    os.makedirs("data", exist_ok=True)
    with open("data/dry_run_results.json", "w", encoding="utf-8") as f:
        json.dump(results_payload, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Validação concluída. {len(selected_jobs)} vagas processadas com sucesso.")


if __name__ == "__main__":
    run_dry_search(max_jobs=20)

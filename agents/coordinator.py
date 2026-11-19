"""Agente Coordenador e Orquestrador do Pipeline do Radar de Vagas."""

import os
import yaml
import logging
from typing import Dict, Any, List

from agents.harvester import JobHarvesterAgent
from agents.scorer import FitScorerAgent
from src.core.database import DatabaseManager
from src.core.deduplication import DeduplicationEngine
from src.core.models import JobOpportunity
from src.exporters.excel_exporter import ExcelExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RadarDeVagas.Coordinator")


class CoordinatorAgent:
    """Coordena o fluxo completo do Radar de Vagas:
    Configuração -> Coleta -> Deduplicação -> Scoring -> Persistência -> Exportação.
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.db = DatabaseManager()
        self.exporter = ExcelExporter()
        self._load_configs()

        self.harvester = JobHarvesterAgent(self.search_queries_cfg)
        self.scorer = FitScorerAgent(
            profile_config=self.profile_cfg,
            scoring_rules=self.scoring_rules_cfg,
            keywords_config=self.keywords_cfg
        )

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        filepath = os.path.join(self.config_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_configs(self):
        """Carrega todos os arquivos de configuração do diretório /config."""
        self.profile_cfg = self._load_yaml("profile.yaml")
        self.cargos_cfg = self._load_yaml("cargos.yaml")
        self.localizacao_cfg = self._load_yaml("localizacao.yaml")
        self.keywords_cfg = self._load_yaml("keywords.yaml")
        self.scoring_rules_cfg = self._load_yaml("scoring_rules.yaml")
        self.dedup_cfg = self._load_yaml("deduplication_rules.yaml")
        self.search_queries_cfg = self._load_yaml("search_queries.yaml")

    def run_pipeline(self, max_queries: int = 5) -> Dict[str, Any]:
        """Executa uma rodada completa de monitoramento e triagem de vagas."""
        logger.info("Iniciando Pipeline do RADAR DE VAGAS...")

        # 1. Montagem das queries prioritárias
        queries_alta = self.cargos_cfg.get("prioridade_alta", [])
        queries_media = self.cargos_cfg.get("prioridade_media", [])
        search_terms = (queries_alta + queries_media)[:max_queries]

        locations = ["Campinas, SP", "Remoto", "Brasil"]

        # 2. Coleta via Harvester
        logger.info(f"Disparando coleta para os termos: {search_terms}")
        raw_jobs = self.harvester.search_all_sources(search_terms, locations)
        logger.info(f"Total de vagas brutas coletadas: {len(raw_jobs)}")

        if not raw_jobs:
            logger.warning("Nenhuma vaga encontrada na rodada de busca.")
            return {"status": "success", "total_coletadas": 0, "novas_vagas": 0}

        # 3. Deduplicação em tempo real
        seen_hashes = self.db.get_all_seen_hashes()
        unique_jobs: List[JobOpportunity] = []
        duplicadas_count = 0

        for job in raw_jobs:
            if not job.id:
                job.id = DeduplicationEngine.generate_job_hash(job.empresa, job.titulo, job.localizacao, job.url)
            
            if job.id not in seen_hashes:
                seen_hashes.add(job.id)
                unique_jobs.append(job)
            else:
                duplicadas_count += 1

        logger.info(f"Vagas inéditas identificadas: {len(unique_jobs)} (Duplicadas descartadas: {duplicadas_count})")

        # 4. Avaliação e Ranqueamento (Fit Score)
        scored_jobs = self.scorer.score_jobs(unique_jobs)

        # 5. Persistência no Banco SQLite
        inserted = self.db.save_jobs_batch(scored_jobs)
        logger.info(f"Vagas gravadas com sucesso no histórico SQLite: {inserted}")

        # 6. Exportação para Planilha Excel
        output_file = self.exporter.export_jobs(scored_jobs)
        logger.info(f"Planilha atualizada gerada em: {output_file}")

        # Estatísticas da rodada
        top_tier = [j for j in scored_jobs if j.score >= 80]
        return {
            "status": "success",
            "total_coletadas": len(raw_jobs),
            "duplicadas_descartadas": duplicadas_count,
            "novas_inseridas": len(scored_jobs),
            "vagas_alta_prioridade": len(top_tier),
            "planilha_gerada": output_file
        }

"""Agente Analisador e Ranqueador de Aderência (Fit Scorer)."""

import logging
from typing import List, Tuple
from src.core.models import JobOpportunity, FitScoreResult
from src.core.scorer import FitScorer

logger = logging.getLogger("RadarDeVagas.FitScorer")


class FitScorerAgent:
    """Responsável por avaliar e ranquear as vagas com base nas regras de pontuação."""

    def __init__(self, profile_config: dict = None, scoring_rules: dict = None, keywords_config: dict = None):
        self.profile = profile_config or {}
        self.rules = scoring_rules or {}
        self.keywords = keywords_config or {}

    def score_jobs(self, jobs: List[JobOpportunity]) -> List[JobOpportunity]:
        """Calcula o Fit Score para cada vaga e retorna a lista classificada e ordenada."""
        scored_jobs: List[JobOpportunity] = []

        for job in jobs:
            try:
                result = FitScorer.evaluate_job(job)
                # Ignora vagas descartadas por filtros negativos severos
                if result.score_total > 0:
                    scored_jobs.append(job)
            except Exception as e:
                logger.error(f"Erro ao calcular score para a vaga '{job.titulo}': {e}")
                scored_jobs.append(job)

        # Ordenação decrescente pelo Fit Score
        scored_jobs.sort(key=lambda x: x.score, reverse=True)
        return scored_jobs

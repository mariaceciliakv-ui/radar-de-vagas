"""Testes unitários para validação do Agente de Vagas e motores de scoring e deduplicação."""

import unittest
from src.core.models import JobOpportunity
from src.core.deduplication import DeduplicationEngine
from src.core.scorer import FitScorer
from src.core.database import DatabaseManager


class TestJobAgent(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")

    def test_deduplication_url_sanitization(self):
        dirty_url = "https://www.linkedin.com/jobs/view/3847291823/?utm_source=share&utm_medium=member_desktop&refId=abc12345"
        clean_url = DeduplicationEngine.sanitize_url(dirty_url)
        self.assertEqual(clean_url, "https://www.linkedin.com/jobs/view/3847291823")

    def test_fit_score_calculation(self):
        job = JobOpportunity(
            titulo="Analista de BI Jr / Power BI",
            empresa="Tech Logistics Campinas",
            localizacao="Campinas - SP",
            modalidade="Híbrido",
            descricao="Requisitos: Experiência com Power BI, Excel avançado, criação de dashboards, acompanhamento de indicadores e KPIs. Vivência em SAP ou logística é um diferencial. Conhecimento em SQL e DAX desejável.",
            url="https://linkedin.com/jobs/view/12345",
            fonte="LinkedIn"
        )
        result = FitScorer.evaluate_job(job)
        self.assertGreaterEqual(result.score_total, 65.0)
        self.assertEqual(result.classificacao, "Alta Aderência")
        self.assertIn("Power Bi", job.pontos_fortes)
        self.assertIn("Excel", job.pontos_fortes)
        self.assertIn("SAP", job.pontos_fortes)
        self.assertIn("SQL", job.oportunidades_desenvolvimento)

    def test_negative_filter_exclusion(self):
        job_estagio = JobOpportunity(
            titulo="Estágio em Engenharia Civil",
            empresa="Construtora X",
            localizacao="Campinas - SP",
            modalidade="Presencial",
            descricao="Vaga de estágio para estudantes de engenharia.",
            url="https://vagas.com/123",
            fonte="Vagas.com"
        )
        result = FitScorer.evaluate_job(job_estagio)
        self.assertEqual(result.score_total, 0.0)
        self.assertIn("Descartada", result.classificacao)

    def test_database_persistence(self):
        job = JobOpportunity(
            id="hash_test_123",
            titulo="Analista de Dados Jr",
            empresa="Empresa Teste",
            localizacao="Remoto",
            modalidade="Remoto",
            url="https://example.com/job1",
            fonte="Indeed"
        )
        # Primeira inserção
        saved = self.db.save_job(job)
        self.assertTrue(saved)
        # Segunda inserção (duplicada)
        self.assertTrue(self.db.is_job_seen(job.id, job.url))


if __name__ == "__main__":
    unittest.main()

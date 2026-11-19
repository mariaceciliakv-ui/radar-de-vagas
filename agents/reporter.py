"""Agente Gerador de Relatórios e Resumos Executivos."""

class ReporterAgent:
    """Responsável por consolidar os resultados de cada rodada:
    - Métricas de execução (total coletado, deduplicado, ranqueado)
    - Top 5 melhores oportunidades
    - Geração de arquivos em Markdown/HTML no diretório /reports
    """

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir

    def generate_execution_summary(self, summary_data: dict) -> str:
        """Gera o relatório da execução em Markdown."""
        raise NotImplementedError("Implementação do gerador de relatórios agendada para a próxima fase.")

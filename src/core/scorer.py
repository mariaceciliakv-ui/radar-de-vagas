"""Motor de Avaliação e Cálculo de Aderência (Fit Score: 0 a 100)."""

import re
from typing import Dict, Any, List, Tuple
from .models import JobOpportunity, FitScoreResult
from .deduplication import DeduplicationEngine


class FitScorer:
    """Calcula a aderência de cada vaga em relação ao perfil da candidata."""

    # 1. Habilidades Consolidadas (Base Forte: 35 pts max)
    SKILLS_CONSOLIDADAS = {
        "power bi": ["power bi", "powerbi", "pbi", "microsoft power bi", "ms power bi"],
        "excel": ["excel", "excel avancado", "planilhas", "tabelas dinamicas", "vba"],
        "sap": ["sap", "erp sap", "sap r/3", "sap s/4hana", "sap business one", "modulo sap"],
        "crm": ["crm", "salesforce", "hubspot", "gestao de clientes", "rd station", "pipedrive"],
        "indicadores": ["indicadores", "kpi", "kpis", "metricas", "slas", "painel de indicadores"],
        "processos": ["processos", "mapeamento de processos", "bpmn", "melhoria continua", "fluxogramas"],
        "logistica": ["logistica", "supply chain", "cadeia de suprimentos", "expedicao", "estoque", "armazenagem"],
        "operacoes": ["operacoes", "back office", "rotinas administrativas", "faturamento", "pedidos", "suporte operacional"],
        "pcp": ["pcp", "planejamento e controle da producao", "planejamento operacional"],
        "comercial": ["comercial", "inteligencia comercial", "sales ops", "relacionamento com clientes", "suporte a vendas"]
    }

    # 2. Oportunidades de Desenvolvimento Técnico (10 pts max)
    SKILLS_DESENVOLVIMENTO = {
        "sql": ["sql", "t-sql", "pl/sql", "postgresql", "mysql", "sql server", "queries"],
        "dax": ["dax", "funcoes dax", "calculos dax"],
        "power query": ["power query", "powerquery", "linguagem m", "m code"],
        "modelagem de dados": ["modelagem de dados", "star schema", "snowflake", "esquema estrela", "tabelas fato e dimensao"],
        "python": ["python", "pandas", "numpy", "analise de dados em python"],
        "etl": ["etl", "pipeline de dados", "extracao e transformacao", "ingestao de dados"],
        "banco de dados": ["banco de dados", "database", "data warehouse", "dw", "modelagem dimensional"]
    }

    # 3. Áreas e Cargos Alvo (20 pts max)
    AREAS_ALVO = [
        "bi", "business intelligence", "dados", "data", "analytics", "business analytics",
        "indicadores", "performance", "metricas", "planejamento", "operacoes", "operations",
        "back office", "backoffice", "logistica", "supply chain", "pcp", "comercial", "sales ops"
    ]

    # 4. Cidades da Região de Campinas (RMC)
    RMC_CIDADES = [
        "campinas", "valinhos", "vinhedo", "hortolandia", "sumare", "paulinia",
        "indaiatuba", "americana", "jaguariuna", "santa barbara doeste", "nova odessa", "jundiai"
    ]

    # 5. Filtros Negativos Severos
    TERMOS_NEGATIVOS = [
        "estagio", "estagiario", "estagiaria", "jovem aprendiz", "menor aprendiz",
        "trainee", "enfermagem", "motorista", "vendedor externo", "balconista",
        "operador de empilhadeira", "auxiliar de limpeza", "torneiro mecanico"
    ]

    @classmethod
    def evaluate_job(cls, job: JobOpportunity) -> FitScoreResult:
        """Avalia a vaga e retorna o detalhamento completo do score."""
        texto_completo = f"{job.titulo} {job.descricao} {job.localizacao} {job.modalidade}".lower()
        texto_norm = DeduplicationEngine.normalize_text(texto_completo)
        titulo_norm = DeduplicationEngine.normalize_text(job.titulo)

        # Checagem de filtro negativo (estágios ou funções braçais não correlatas)
        for neg in cls.TERMOS_NEGATIVOS:
            if re.search(r'\b' + re.escape(neg) + r'\b', titulo_norm):
                return FitScoreResult(
                    score_total=0.0,
                    classificacao="Descartada (Termo Excludente)",
                    score_skills=0.0,
                    score_desenvolvimento=0.0,
                    score_area_cargo=0.0,
                    score_modalidade=0.0,
                    score_localidade=0.0,
                    score_recencia=0.0,
                    pontos_fortes=[],
                    oportunidades_desenvolvimento=[],
                    justificativa=f"Vaga descartada por conter termo incompatível: '{neg}' no título."
                )

        pontos_fortes: List[str] = []
        oportunidades_desenvolvimento: List[str] = []
        tecnologias_detectadas: List[str] = []

        # 1. Avaliação de Competências Consolidadas (Max 35 pts)
        score_skills = 0.0
        pts_por_skill_forte = 35.0 / len(cls.SKILLS_CONSOLIDADAS)
        siglas = {"sap", "crm", "pcp", "sql", "dax", "bi", "etl", "kpi", "kpis"}
        
        def format_skill_name(name: str) -> str:
            return name.upper() if name.lower() in siglas else name.title()

        for skill_nome, aliases in cls.SKILLS_CONSOLIDADAS.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', texto_norm):
                    score_skills += pts_por_skill_forte
                    formatted_name = format_skill_name(skill_nome)
                    pontos_fortes.append(formatted_name)
                    tecnologias_detectadas.append(formatted_name)
                    break
        score_skills = min(score_skills, 35.0)

        # 2. Avaliação de Oportunidades de Desenvolvimento (Max 10 pts)
        score_desenvolvimento = 0.0
        pts_por_dev = 10.0 / len(cls.SKILLS_DESENVOLVIMENTO)
        for skill_dev, aliases in cls.SKILLS_DESENVOLVIMENTO.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', texto_norm):
                    score_desenvolvimento += pts_por_dev
                    oportunidades_desenvolvimento.append(skill_dev.upper() if len(skill_dev) <= 4 else skill_dev.title())
                    tecnologias_detectadas.append(skill_dev.upper() if len(skill_dev) <= 4 else skill_dev.title())
                    break
        score_desenvolvimento = min(score_desenvolvimento, 10.0)

        # 3. Alinhamento de Área e Título do Cargo (Max 20 pts)
        score_area_cargo = 0.0
        match_count = 0
        for area in cls.AREAS_ALVO:
            if re.search(r'\b' + re.escape(area) + r'\b', titulo_norm):
                match_count += 1
        if match_count >= 2:
            score_area_cargo = 20.0
        elif match_count == 1:
            score_area_cargo = 15.0
        else:
            # Se não está no título, verifica na descrição
            for area in cls.AREAS_ALVO:
                if re.search(r'\b' + re.escape(area) + r'\b', texto_norm):
                    score_area_cargo = 10.0
                    break

        # 4. Modalidade de Trabalho (Max 20 pts)
        score_modalidade = 0.0
        modalidade_norm = DeduplicationEngine.normalize_text(job.modalidade)
        if any(term in modalidade_norm or term in texto_norm for term in ["remoto", "home office", "teletrabalho"]):
            score_modalidade = 20.0
            job.modalidade = "Remoto"
        elif any(term in modalidade_norm or term in texto_norm for term in ["hibrido", "hybrid", "modelo hibrido"]):
            score_modalidade = 18.0
            job.modalidade = "Híbrido"
        else:
            # Presencial
            score_modalidade = 12.0
            job.modalidade = "Presencial"

        # 5. Localidade (Max 10 pts)
        score_localidade = 0.0
        local_norm = DeduplicationEngine.normalize_text(job.localizacao)
        if job.modalidade == "Remoto":
            score_localidade = 10.0
        elif "campinas" in local_norm:
            score_localidade = 10.0
        elif any(cidade in local_norm for cidade in cls.RMC_CIDADES):
            score_localidade = 9.0
        elif "sao paulo" in local_norm or "sp" in local_norm:
            score_localidade = 7.0 if job.modalidade == "Híbrido" else 3.0
        else:
            score_localidade = 0.0

        # 6. Recência (Max 5 pts bônus)
        score_recencia = 0.0
        data_norm = DeduplicationEngine.normalize_text(job.data_publicacao or "")
        if any(term in data_norm for term in ["hoje", "hora", "horas", "1 dia", "2 dias", "3 dias", "recente"]):
            score_recencia = 5.0
        else:
            score_recencia = 2.5

        score_total = min(round(
            score_skills + score_desenvolvimento + score_area_cargo + 
            score_modalidade + score_localidade + score_recencia, 1
        ), 100.0)

        # Classificação de Prioridade
        if score_total >= 80.0:
            classificacao = "Excelente (Prioridade Máxima)"
        elif score_total >= 65.0:
            classificacao = "Alta Aderência"
        elif score_total >= 45.0:
            classificacao = "Média Aderência"
        else:
            classificacao = "Baixa Aderência"

        # Atualiza a própria vaga com os campos enriquecidos
        job.score = score_total
        job.classificacao = classificacao
        job.pontos_fortes = list(set(pontos_fortes))
        job.oportunidades_desenvolvimento = list(set(oportunidades_desenvolvimento))
        job.tecnologias = list(set(tecnologias_detectadas))

        justificativa = (
            f"Fit Score: {score_total}%. "
            f"Skills identificadas: {', '.join(job.pontos_fortes) if job.pontos_fortes else 'Gerais'}. "
            f"Oportunidades de crescimento: {', '.join(job.oportunidades_desenvolvimento) if job.oportunidades_desenvolvimento else 'N/A'}."
        )

        return FitScoreResult(
            score_total=score_total,
            classificacao=classificacao,
            score_skills=score_skills,
            score_desenvolvimento=score_desenvolvimento,
            score_area_cargo=score_area_cargo,
            score_modalidade=score_modalidade,
            score_localidade=score_localidade,
            score_recencia=score_recencia,
            pontos_fortes=job.pontos_fortes,
            oportunidades_desenvolvimento=job.oportunidades_desenvolvimento,
            justificativa=justificativa
        )

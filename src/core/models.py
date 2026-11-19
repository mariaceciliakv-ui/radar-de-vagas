"""Modelos de dados estruturados para o Radar de Vagas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class JobOpportunity(BaseModel):
    """Representa uma oportunidade de trabalho coletada e normalizada."""
    id: Optional[str] = Field(default=None, description="Identificador único ou hash SHA-256")
    titulo: str = Field(description="Título do cargo anunciado")
    empresa: str = Field(description="Nome da empresa contratante")
    localizacao: str = Field(default="Não especificada", description="Cidade/UF ou localização declarada")
    modalidade: str = Field(default="Presencial", description="Remoto, Híbrido ou Presencial")
    salario: Optional[str] = Field(default="Não informado", description="Faixa salarial quando disponível")
    data_publicacao: Optional[str] = Field(default="Recente", description="Data ou tempo relativo de publicação")
    descricao: str = Field(default="", description="Descrição completa ou requisitos capturados")
    url: str = Field(description="URL canônica da vaga")
    fonte: str = Field(description="Plataforma de origem (LinkedIn, Indeed, Gupy, etc.)")
    requisitos: List[str] = Field(default_factory=list, description="Lista de requisitos identificados")
    tecnologias: List[str] = Field(default_factory=list, description="Ferramentas e tecnologias mencionadas")
    
    # Métricas calculadas
    score: float = Field(default=0.0, description="Pontuação de aderência (0 a 100)")
    classificacao: str = Field(default="Baixa", description="Prioridade: Excelente, Alta, Média, Baixa")
    pontos_fortes: List[str] = Field(default_factory=list, description="Competências da candidata presentes na vaga")
    oportunidades_desenvolvimento: List[str] = Field(default_factory=list, description="Tecnologias que permitem aprendizado")
    coletado_em: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Acompanhamento de Candidatura
    status_candidatura: str = Field(default="Não iniciada", description="Status da candidatura (Não iniciada, Em análise, Candidatura em preenchimento, Aguardando minha revisão, Enviada, Vaga encerrada, Link inválido, Bloqueada ou exige ação manual)")
    data_tentativa: Optional[str] = Field(default=None, description="Data e hora da tentativa de candidatura")
    etapa_alcancada: Optional[str] = Field(default="Nenhuma", description="Última etapa alcançada no processo")
    campos_pendentes: Optional[str] = Field(default="-", description="Campos ou perguntas pendentes de aprovação")
    proxima_acao: Optional[str] = Field(default="Aguardando início", description="Próximo passo a ser realizado")


class FitScoreResult(BaseModel):
    """Resultado detalhado do cálculo de aderência."""
    score_total: float
    classificacao: str
    score_skills: float
    score_desenvolvimento: float
    score_area_cargo: float
    score_modalidade: float
    score_localidade: float
    score_recencia: float
    pontos_fortes: List[str]
    oportunidades_desenvolvimento: List[str]
    justificativa: str

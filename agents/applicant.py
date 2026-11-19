"""Agente de Execução Assistida de Candidatura (ApplicationAgent).

Responsável por:
1. Ler a planilha de vagas e selecionar oportunidades não processadas (por score e recência).
2. Inspecionar o link oficial da vaga no navegador e verificar validade/abertura.
3. Identificar a plataforma (Indeed, LinkedIn, Gupy, etc.) e as etapas de candidatura.
4. Mapear formulários usando EXCLUSIVAMENTE os dados reais e aprovados da candidata (Zero Alucinação).
5. Interromper e solicitar intervenção humana para CAPTCHA, login fechado, testes técnicos ou perguntas desconhecidas.
6. Atualizar a planilha com o status, timestamp, etapa alcançada, pendências e próxima ação.
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.core.models import JobOpportunity
from src.exporters.excel_exporter import ExcelExporter

logger = logging.getLogger("RadarDeVagas.Applicant")


class ApplicationAgent:
    """Gerencia a triagem, inspeção e execução assistida de candidaturas."""

    STATUS_NAO_INICIADA = "Não iniciada"
    STATUS_EM_ANALISE = "Em análise"
    STATUS_PREENCHIMENTO = "Candidatura em preenchimento"
    STATUS_AGUARDANDO_REVISAO = "Aguardando minha revisão"
    STATUS_ENVIADA = "Enviada"
    STATUS_ENCERRADA = "Vaga encerrada"
    STATUS_LINK_INVALIDO = "Link inválido"
    STATUS_BLOQUEADA_MANUAL = "Bloqueada ou exige ação manual"

    def __init__(self, config_dir: str = "config", excel_path: str = "data/output/Radar_Vagas_Data.xlsx"):
        self.config_dir = config_dir
        self.excel_path = excel_path
        self.exporter = ExcelExporter()
        self.profile = self.load_profile()

    def load_profile(self) -> Dict[str, Any]:
        """Carrega os dados cadastrais e profissionais oficiais da candidata."""
        profile_path = os.path.join(self.config_dir, "profile.yaml")
        if not os.path.exists(profile_path):
            logger.warning(f"Arquivo de perfil não encontrado em {profile_path}")
            return {}
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("candidata", {})
        except Exception as e:
            logger.error(f"Erro ao carregar perfil: {e}")
            return {}

    def get_pending_jobs(self, limit: int = 10) -> List[JobOpportunity]:
        """Recupera vagas não iniciadas ou em análise da planilha, priorizando maior aderência."""
        all_jobs = self.exporter.read_existing_jobs(self.excel_path)
        
        pending = [
            j for j in all_jobs
            if not j.status_candidatura or j.status_candidatura in [self.STATUS_NAO_INICIADA, self.STATUS_EM_ANALISE]
        ]
        
        # Ordenar por Score decrescente
        pending.sort(key=lambda x: x.score, reverse=True)
        return pending[:limit]

    def inspect_job_url(self, job: JobOpportunity) -> Dict[str, Any]:
        """Avalia a estrutura da URL e a plataforma da vaga."""
        url = job.url.strip()
        analysis = {
            "valido": bool(url and url.startswith("http")),
            "plataforma": job.fonte or "Desconhecida",
            "tipo_processo": "Desconhecido",
            "bloqueio_esperado": False,
            "observacoes": []
        }

        if not analysis["valido"]:
            analysis["observacoes"].append("Link ausente ou malformado.")
            return analysis

        url_lower = url.lower()

        if "indeed" in url_lower:
            analysis["plataforma"] = "Indeed"
            analysis["tipo_processo"] = "Candidatura Simplificada ou Redirecionamento Externo"
            analysis["observacoes"].append("Indeed pode solicitar login de conta ou verificação anti-bot Cloudflare.")
        elif "linkedin" in url_lower:
            analysis["plataforma"] = "LinkedIn"
            analysis["tipo_processo"] = "Candidatura Simplificada (Easy Apply) ou Externa"
            analysis["observacoes"].append("LinkedIn exige sessão autenticada para candidatura direta.")
        elif "gupy.io" in url_lower:
            analysis["plataforma"] = "Gupy"
            analysis["tipo_processo"] = "Portal Gupy (Cadastro + Testes Comportamentais)"
            analysis["observacoes"].append("Gupy frequentemente exige preenchimento de testes de perfil/fit cultural.")
        elif "glassdoor" in url_lower:
            analysis["plataforma"] = "Glassdoor"
            analysis["tipo_processo"] = "Redirecionamento para parceiro/empresa"
        else:
            analysis["plataforma"] = "Site Próprio / ATS"
            analysis["tipo_processo"] = "Formulário Web"

        return analysis

    def prepare_application_draft(self, job: JobOpportunity) -> Dict[str, Any]:
        """Mapeia os dados reais da candidata com base nos campos padronizados."""
        c = self.profile
        contato = c.get("contato", {})
        endereco = contato.get("endereco", {})
        redes = contato.get("redes_e_links", {})

        draft = {
            "vaga": {
                "titulo": job.titulo,
                "empresa": job.empresa,
                "modalidade": job.modalidade,
                "score": f"{job.score:.1f}%",
                "url": job.url
            },
            "dados_pessoais": {
                "nome_completo": c.get("nome", "Maria Cecília Jesus Oliveira"),
                "email": contato.get("email", "mariacecilia.kv@gmail.com"),
                "telefone_principal": "(19) 98735-3831",
                "telefone_secundario": "(11) 92039-6714",
                "localizacao": f"{endereco.get('bairro', 'Jardim Fernanda')}, {endereco.get('cidade', 'Campinas')} - {endereco.get('estado', 'SP')}",
                "cep": endereco.get("cep", "07906-603"),
                "cnh": c.get("cnh", "Categoria B")
            },
            "links_profissionais": {
                "linkedin": redes.get("linkedin", "https://www.linkedin.com/in/maria-c-j-oliveira"),
                "portfolio_site": redes.get("site", "https://sites.google.com/view/mycvbymaria")
            },
            "formacao_academica": c.get("formacao_academica", {}),
            "experiencias_destaque": [
                {
                    "cargo": "Subgerente Administrativo e Operacional",
                    "empresa": "Claudinha Lanches",
                    "foco": "Operações, Dashboards, Gestão de Estoque, Sistemas (Yooga/iFood)"
                },
                {
                    "cargo": "Analista de Negócios",
                    "empresa": "Aperam Serviços e Soluções",
                    "foco": "SAP Key User, CRM, Faturamento, Operações Comerciais, Indicadores"
                }
            ],
            "competencias_chave": [
                "Power BI", "Excel Avançado", "SAP S/4HANA", "CRM", "Gestão de Indicadores",
                "Logística", "Comércio Exterior", "Automação de Processos"
            ],
            "curriculo_anexo_disponivel": os.path.exists("config/curriculo.html") or os.path.exists("config/curriculo_maria_cecilia_oliveira.pdf"),
            "campos_bloqueados_ou_requeridos": [
                "Pretensão Salarial específica (caso obrigatória)",
                "Autenticação de Conta / Senha na plataforma",
                "Resolução de CAPTCHA ou testes de perfil comportamental"
            ]
        }
        return draft

    def update_job_status(
        self,
        job_url: str,
        status: str,
        etapa: str = "Nenhuma",
        pendentes: str = "-",
        proxima_acao: str = "Aguardando início"
    ) -> bool:
        """Salva a evolução do processo de candidatura na planilha oficial."""
        return self.exporter.update_application_status(
            job_url=job_url,
            status=status,
            etapa=etapa,
            pendentes=pendentes,
            proxima_acao=proxima_acao,
            file_path=self.excel_path
        )

    def check_session_status(self, page, platform: str) -> bool:
        """Verifica se a página aberta no navegador possui sessão ativa."""
        try:
            url = page.url.lower()
            content = page.content().lower()
            if platform.lower() == "indeed":
                if "security check" in content or "bot-detection" in url:
                    return False
                if "entrar" not in content and ("sair" in content or "minha conta" in content or "gnav-account" in content):
                    return True
            elif platform.lower() == "linkedin":
                if "feed" in url and "login" not in url and "authwall" not in url:
                    return True
            elif platform.lower() == "gupy":
                if "candidato" in url or "dashboard" in url or "perfil" in url:
                    return True
                if "login" not in url and "entrar" not in content:
                    return True
        except Exception as e:
            logger.debug(f"Erro ao verificar sessão: {e}")
        return False

    def inspect_job_in_browser(self, job: JobOpportunity, profile_dir: str = "data/browser_profile") -> Dict[str, Any]:
        """Abre a vaga no navegador com perfil persistente e verifica autenticação e barreiras."""
        from playwright.sync_api import sync_playwright

        os.makedirs(profile_dir, exist_ok=True)
        inspection = self.inspect_job_url(job)
        platform = inspection["plataforma"]

        result = {
            "plataforma": platform,
            "autenticado": False,
            "vaga_aberta": False,
            "bloqueio_encontrado": None,
            "etapa": "Início da inspeção",
            "pendencias": "-",
            "proxima_acao": "Aguardando início"
        }

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=os.path.abspath(profile_dir),
                    channel="chrome",
                    headless=False,
                    args=["--start-maximized", "--no-first-run", "--no-default-browser-check"]
                )
                page = context.pages[0] if context.pages else context.new_page()

                # Navegar para a vaga
                page.goto(job.url, timeout=30000)
                page.wait_for_timeout(3000)

                url_atual = page.url.lower()
                content = page.content().lower()
                title = page.title()

                # 1. Verificar bloqueio ou exigência de login
                if "security check" in content or "bot-detection" in url_atual:
                    result["bloqueio_encontrado"] = "Verificação de segurança / Anti-bot Indeed"
                    result["etapa"] = "Bloqueio de segurança na página da vaga"
                    result["pendencias"] = "Exige login manual na janela do navegador"
                    result["proxima_acao"] = "Usuária realizar login manual no Indeed"
                    result["autenticado"] = False
                elif "login" in url_atual or "authwall" in url_atual:
                    result["bloqueio_encontrado"] = f"Redirecionamento para tela de login ({platform})"
                    result["etapa"] = "Sessão não autenticada / expirada"
                    result["pendencias"] = f"Realizar login manual no {platform}"
                    result["proxima_acao"] = f"Usuária autenticar manualmente no {platform}"
                    result["autenticado"] = False
                else:
                    result["autenticado"] = True
                    result["vaga_aberta"] = True
                    result["etapa"] = "Página da vaga carregada com sucesso"
                    result["pendencias"] = "Revisar resumo e autorizar preenchimento"
                    result["proxima_acao"] = "Apresentar resumo e aguardar aprovação da usuária"

                context.close()
        except Exception as e:
            result["bloqueio_encontrado"] = f"Erro no navegador: {str(e)[:80]}"
            result["etapa"] = "Erro de navegação"
            result["proxima_acao"] = "Verificar conectividade do navegador"

        return result


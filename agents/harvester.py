"""Agente Harvester de Vagas Multi-fonte (LinkedIn, Indeed, Glassdoor, Gupy, InfoJobs, etc.)."""

import logging
import time
import random
from typing import List, Dict, Any, Optional
import urllib.parse
import requests
from bs4 import BeautifulSoup

from src.core.models import JobOpportunity
from src.core.deduplication import DeduplicationEngine

logger = logging.getLogger("RadarDeVagas.Harvester")


class JobHarvesterAgent:
    """Coleta oportunidades em múltiplas fontes públicas com sanitização e extração de atributos."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ]

    def __init__(self, search_config: Optional[Dict[str, Any]] = None):
        self.config = search_config or {}
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "DNT": "1"
        }

    def search_all_sources(self, queries: List[str], locations: List[str], max_results_per_query: int = 15) -> List[JobOpportunity]:
        """Orquestra a busca consolidada em múltiplas plataformas públicas."""
        all_jobs: List[JobOpportunity] = []

        # 1. Busca via JobSpy (LinkedIn, Indeed, Glassdoor)
        try:
            from jobspy import scrape_jobs
            jobspy_available = True
        except ImportError:
            jobspy_available = False
            logger.warning("Biblioteca python-jobspy não instalada. Usando extratores web diretos.")

        if jobspy_available:
            for query in queries:
                for loc in locations:
                    try:
                        logger.info(f"Buscando via JobSpy: '{query}' em '{loc}'...")
                        df = scrape_jobs(
                            site_name=["linkedin", "indeed", "glassdoor"],
                            search_term=query,
                            location=loc,
                            results_wanted=max_results_per_query,
                            country_indeed='brazil',
                            is_remote=("remoto" in loc.lower() or "brasil" in loc.lower())
                        )
                        if df is not None and not df.empty:
                            for _, row in df.iterrows():
                                job = self._parse_jobspy_row(row)
                                if job:
                                    all_jobs.append(job)
                        time.sleep(random.uniform(2.0, 4.0)) # Delay ético
                    except Exception as e:
                        logger.error(f"Erro ao buscar '{query}' em '{loc}' via JobSpy: {e}")

        # 2. Busca Complementar em Portais Nacionais (Gupy / InfoJobs / Remotar)
        for query in queries[:3]: # Termos prioritários
            gupy_jobs = self._search_gupy_public(query)
            all_jobs.extend(gupy_jobs)
            time.sleep(1.5)

        return all_jobs

    def _parse_jobspy_row(self, row: Any) -> Optional[JobOpportunity]:
        """Normaliza os dados retornados pelo JobSpy em um modelo JobOpportunity."""
        try:
            titulo = str(row.get("title", "")).strip()
            empresa = str(row.get("company", "")).strip()
            raw_url = str(row.get("job_url", "")).strip()

            if not titulo or not empresa or not raw_url:
                return None

            clean_url = DeduplicationEngine.sanitize_url(raw_url)
            localizacao = str(row.get("location", "Brasil")).strip()
            
            # Modalidade
            is_remote = bool(row.get("is_remote", False))
            modalidade = "Remoto" if is_remote else "Presencial"
            if "hibrid" in localizacao.lower() or "híbrid" in str(row.get("description", "")).lower():
                modalidade = "Híbrido"

            # Salário
            min_amt = row.get("min_amount")
            max_amt = row.get("max_amount")
            currency = str(row.get("currency", "BRL"))
            salario = "A combinar"
            if min_amt and max_amt:
                salario = f"{currency} {min_amt:,.0f} - {max_amt:,.0f}"
            elif min_amt:
                salario = f"A partir de {currency} {min_amt:,.0f}"

            # Data
            date_posted = str(row.get("date_posted", "Recente"))
            descricao = str(row.get("description", ""))
            fonte = str(row.get("site", "Web")).capitalize()

            job_hash = DeduplicationEngine.generate_job_hash(empresa, titulo, localizacao, clean_url)

            return JobOpportunity(
                id=job_hash,
                titulo=titulo,
                empresa=empresa,
                localizacao=localizacao,
                modalidade=modalidade,
                salario=salario,
                data_publicacao=date_posted,
                descricao=descricao,
                url=clean_url,
                fonte=fonte
            )
        except Exception as e:
            logger.debug(f"Erro ao converter linha da vaga: {e}")
            return None

    def _search_gupy_public(self, query: str) -> List[JobOpportunity]:
        """Busca vagas públicas na API / portal aberto do Gupy."""
        jobs: List[JobOpportunity] = []
        try:
            encoded_query = urllib.parse.quote(query)
            api_url = f"https://portal.api.gupy.io/api/v1/jobs?jobName={encoded_query}&limit=10"
            resp = self.session.get(api_url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    titulo = item.get("name", "")
                    empresa = item.get("careerPageName", "Empresa via Gupy")
                    raw_url = item.get("jobUrl", "")
                    clean_url = DeduplicationEngine.sanitize_url(raw_url)
                    
                    workplace = item.get("workplaceType", "").lower()
                    if "remote" in workplace:
                        modalidade = "Remoto"
                    elif "hybrid" in workplace:
                        modalidade = "Híbrido"
                    else:
                        modalidade = "Presencial"

                    cidade = item.get("city", "")
                    uf = item.get("state", "")
                    localizacao = f"{cidade} - {uf}" if cidade and uf else (cidade or uf or "Brasil")

                    job_hash = DeduplicationEngine.generate_job_hash(empresa, titulo, localizacao, clean_url)

                    job = JobOpportunity(
                        id=job_hash,
                        titulo=titulo,
                        empresa=empresa,
                        localizacao=localizacao,
                        modalidade=modalidade,
                        salario="A combinar",
                        data_publicacao=str(item.get("publishedDate", "Recente"))[:10],
                        descricao=item.get("description", ""),
                        url=clean_url,
                        fonte="Gupy"
                    )
                    jobs.append(job)
        except Exception as e:
            logger.debug(f"Aviso na busca pública Gupy para '{query}': {e}")
        return jobs

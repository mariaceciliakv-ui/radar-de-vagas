"""Agente de Mapeamento de Recrutadores e Contatos-Chave (OSINT via Google X-Ray Search).

Este agente identifica APENAS perfis PÚBLICOS e disponíveis na internet aberta.
NÃO realiza login em nenhuma plataforma.
NÃO envia mensagens.
NÃO realiza conexões ou interações.
NÃO acessa dados privados.
Apenas pesquisa, coleta e registra informações públicas para revisão humana.
"""

import sys
import os
import time
import random
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tipos de contato que buscamos (em ordem de prioridade)
# ---------------------------------------------------------------------------
RECRUITER_TITLES = [
    "Talent Acquisition",
    "Tech Recruiter",
    "IT Recruiter",
    "Data Recruiter",
    "Talent Acquisition Partner",
    "Recrutador",
    "Recruiter",
    "People & Talent",
    "Recursos Humanos",
    "HRBP",
    "RH",
]

# Frases usadas para compor o Google X-Ray Search
TITLE_SEARCH_PHRASE = (
    '"Talent Acquisition" OR "Tech Recruiter" OR "IT Recruiter" '
    'OR "Talent Acquisition Partner" OR "Recrutador" OR "Recruiter" '
    'OR "People & Talent" OR "Recursos Humanos" OR "RH" OR "HRBP"'
)

# Headers de browser para evitar bloqueio imediato (apenas Google Search)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xhtml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------
class RecruiterHunterAgent:
    """Localiza profissionais de Recrutamento/RH de empresas com vagas de alta aderência.

    Utiliza Google X-Ray Search (pesquisa pública, sem autenticação) para encontrar
    perfis do LinkedIn publicamente indexados.
    """

    def __init__(self, settings: dict = None, min_score_threshold: float = 65.0):
        self.settings = settings or {}
        self.min_score_threshold = min_score_threshold
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._request_count = 0

    # ------------------------------------------------------------------
    # API pública do agente
    # ------------------------------------------------------------------

    def find_recruiters_for_companies(
        self, companies: List[Dict]
    ) -> List[Dict]:
        """Busca recrutadores para uma lista de empresas.

        Args:
            companies: Lista de dicts com chaves 'empresa' e 'vaga_relacionada'.

        Returns:
            Lista de dicts representando contatos encontrados.
        """
        all_recruiters: List[Dict] = []
        seen_urls: set = set()  # evita duplicatas dentro da mesma execução

        logger.info(f"🔍 Iniciando mapeamento de recrutadores para {len(companies)} empresa(s)...")

        for item in companies:
            company_name = item.get("empresa", "").strip()
            related_job = item.get("vaga_relacionada", "").strip()

            if not company_name:
                continue

            logger.info(f"  → Pesquisando: {company_name}")
            recruiters = self._search_recruiters_for_company(
                company_name=company_name,
                related_job=related_job,
                seen_urls=seen_urls,
            )
            all_recruiters.extend(recruiters)

            # Pausa entre empresas para respeitar rate limits do Google
            self._polite_sleep(min_sec=4, max_sec=9)

        logger.info(f"✅ Mapeamento concluído. {len(all_recruiters)} contato(s) encontrado(s).")
        return all_recruiters

    # ------------------------------------------------------------------
    # Busca por empresa
    # ------------------------------------------------------------------

    def _search_recruiters_for_company(
        self,
        company_name: str,
        related_job: str,
        seen_urls: set,
    ) -> List[Dict]:
        """Executa a busca Google X-Ray para uma empresa específica."""
        results: List[Dict] = []

        query = self._build_google_dork(company_name)
        raw_results = self._google_search(query)

        for item in raw_results:
            url = item.get("url", "")
            name = item.get("name", "")
            title = item.get("title", "")
            location = item.get("location", "")

            # Descartar se URL já foi vista nesta execução
            if url and url in seen_urls:
                continue

            # Descartar se não é um perfil LinkedIn válido
            if not self._is_valid_linkedin_profile(url):
                continue

            # Identificar o tipo de contato
            contact_type = self._classify_contact_type(title)

            recruiter = {
                "empresa": company_name,
                "vaga_relacionada": related_job,
                "nome": name,
                "cargo": title,
                "localidade": location,
                "tipo_contato": contact_type,
                "linkedin_url": url,
                "mapeado_em": datetime.now().strftime("%Y-%m-%d"),
                "prioridade": self._calc_recruiter_priority(contact_type, location),
            }
            results.append(recruiter)

            if url:
                seen_urls.add(url)

        # Fallback ético: se bloqueado por rate-limit, gera link direto de busca no LinkedIn
        if not results:
            safe_company = re.sub(r'[^\w\s\-\.]', '', company_name).strip()
            direct_search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus('recruiter ' + safe_company)}"
            results.append({
                "empresa": company_name,
                "vaga_relacionada": related_job,
                "nome": "RH / Recrutamento",
                "cargo": "Buscar Recrutadores no LinkedIn",
                "localidade": "Brasil",
                "tipo_contato": "Busca Direta",
                "linkedin_url": direct_search_url,
                "mapeado_em": datetime.now().strftime("%Y-%m-%d"),
                "prioridade": "Média",
            })

        return results

    # ------------------------------------------------------------------
    # Construção do Google Dork
    # ------------------------------------------------------------------

    def _build_google_dork(self, company_name: str) -> str:
        """Monta a query de X-Ray Search para o Google.

        Formato: site:linkedin.com/in ("<Cargo1>" OR "<Cargo2>") "<Empresa>"
        """
        # Remover caracteres problemáticos do nome da empresa para a query
        safe_company = re.sub(r'[^\w\s\-\.]', '', company_name).strip()

        query = (
            f'site:linkedin.com/in '
            f'({TITLE_SEARCH_PHRASE}) '
            f'"{safe_company}"'
        )
        return query

    # ------------------------------------------------------------------
    # Execução da busca (Google → DuckDuckGo fallback)
    # ------------------------------------------------------------------

    def _google_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Faz uma requisição ao Google Search e parseia os resultados.

        Se o Google bloquear (CAPTCHA / zero resultados), tenta DuckDuckGo.
        IMPORTANTE: Acessa apenas resultados PÚBLICOS. Sem autenticação.
        """
        self._request_count += 1
        encoded_query = quote_plus(query)

        # ── Tentativa 1: Google ──────────────────────────────────────────────
        google_url = (
            f"https://www.google.com/search"
            f"?q={encoded_query}&num={num_results}&hl=pt-BR&gl=br"
        )
        try:
            resp = self.session.get(google_url, timeout=12)
            if resp.status_code == 200:
                results = self._parse_google_results(resp.text)
                if results:
                    logger.info(f"    📍 Google: {len(results)} perfil(s) encontrado(s).")
                    return results
                else:
                    logger.info("    ⚠ Google: 0 resultados ou bloqueio. Tentando DuckDuckGo...")
            else:
                logger.warning(f"    ⚠ Google retornou status {resp.status_code}. Tentando DuckDuckGo...")
        except requests.exceptions.Timeout:
            logger.warning("    ⚠ Timeout no Google. Tentando DuckDuckGo...")
        except requests.exceptions.RequestException as exc:
            logger.warning(f"    ⚠ Erro Google: {exc}. Tentando DuckDuckGo...")

        # ── Tentativa 2: DuckDuckGo HTML ─────────────────────────────────────
        self._polite_sleep(1.5, 3.0)
        return self._duckduckgo_search(query, num_results)

    def _duckduckgo_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Busca via DuckDuckGo HTML (sem API key, apenas HTML público)."""
        encoded_query = quote_plus(query)
        ddg_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        try:
            resp = self.session.get(ddg_url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"    ⚠ DuckDuckGo retornou status {resp.status_code}.")
                return []
            results = self._parse_ddg_results(resp.text)
            logger.info(f"    📍 DuckDuckGo: {len(results)} perfil(s) encontrado(s).")
            return results
        except Exception as exc:
            logger.warning(f"    ⚠ Erro DuckDuckGo: {exc}")
            return []

    def _parse_ddg_results(self, html: str) -> List[Dict]:
        """Parseia resultados HTML do DuckDuckGo."""
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for result in soup.select(".result__body, .results_links_deep .result"):
            link_tag = result.select_one("a.result__url, a.result__a")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            # DuckDuckGo wraps links: //duckduckgo.com/l/?uddg=https%3A%2F%2Flinkedin...
            clean_url = self._extract_ddg_url(href)
            if not clean_url or "linkedin.com/in/" not in clean_url:
                continue

            title_tag = result.select_one("a.result__a, h2")
            raw_title = title_tag.get_text(separator=" ", strip=True) if title_tag else ""

            snippet_tag = result.select_one(".result__snippet, .result__body")
            snippet = snippet_tag.get_text(separator=" ", strip=True) if snippet_tag else ""

            name, cargo, location = self._parse_linkedin_title(raw_title, snippet)
            results.append({
                "url": clean_url,
                "name": name,
                "title": cargo,
                "location": location,
            })

        return results

    def _extract_ddg_url(self, href: str) -> Optional[str]:
        """Extrai URL real do redirecionador DuckDuckGo."""
        from urllib.parse import unquote, urlparse, parse_qs
        if not href:
            return None
        # Formato: //duckduckgo.com/l/?uddg=URL_ENCODED
        parsed = urlparse(href if href.startswith("http") else "https:" + href)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
        # URL direta
        if "linkedin.com" in href:
            return href
        return None

    def _parse_google_results(self, html: str) -> List[Dict]:
        """Extrai perfis LinkedIn dos resultados da página do Google."""
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Bloqueio do Google (CAPTCHA ou "unusual traffic")
        if "unusual traffic" in html.lower() or "captcha" in html.lower():
            logger.warning("    ⚠ Google identificou tráfego automatizado. Aguardando...")
            time.sleep(60)
            return []

        # Iterar sobre os blocos de resultado orgânico do Google
        for block in soup.select("div.g, div[data-hveid], div.tF2Cxc"):
            link_tag = block.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            # Filtrar apenas links LinkedIn
            if "linkedin.com/in/" not in href:
                continue

            # Limpar a URL (remover parâmetros Google)
            clean_url = self._clean_google_redirect(href)
            if not clean_url:
                continue

            # Extrair título do resultado (geralmente "Nome - Cargo - Empresa | LinkedIn")
            title_tag = block.find("h3")
            raw_title = title_tag.get_text(separator=" ", strip=True) if title_tag else ""

            # Extrair snippet (descrição abaixo do título)
            snippet_tag = block.find("div", class_=re.compile(r"VwiC3b|s3v9rd|yXK7lf"))
            snippet = snippet_tag.get_text(separator=" ", strip=True) if snippet_tag else ""

            name, cargo, location = self._parse_linkedin_title(raw_title, snippet)

            results.append({
                "url": clean_url,
                "name": name,
                "title": cargo,
                "location": location,
            })

        return results

    # ------------------------------------------------------------------
    # Parsing de título do resultado do Google
    # ------------------------------------------------------------------

    def _parse_linkedin_title(
        self, raw_title: str, snippet: str
    ) -> tuple:
        """Extrai Nome, Cargo e Localidade do título/snippet de resultado Google.

        Formato típico: "Nome Sobrenome - Cargo na Empresa | LinkedIn"
        """
        # Remover sufixo " | LinkedIn"
        clean = re.sub(r'\s*\|\s*LinkedIn.*$', '', raw_title, flags=re.IGNORECASE).strip()
        # Remover sufixo " - LinkedIn" alternativo
        clean = re.sub(r'\s*-\s*LinkedIn.*$', '', clean, flags=re.IGNORECASE).strip()

        parts = [p.strip() for p in clean.split(" - ")]

        name = parts[0] if len(parts) > 0 else ""
        cargo = parts[1] if len(parts) > 1 else ""

        # Tentar extrair localidade do snippet (ex: "São Paulo, Brasil")
        location = ""
        loc_match = re.search(
            r'(Campinas|São Paulo|SP|RJ|Brasil|Remote|Remoto|Hybrid|Híbrido'
            r'|Paulínia|Sumaré|Hortolândia|Jundiaí|Indaiatuba)',
            snippet, flags=re.IGNORECASE
        )
        if loc_match:
            # Pegar um contexto maior ao redor do match
            start = max(0, loc_match.start() - 5)
            end = min(len(snippet), loc_match.end() + 20)
            location = snippet[start:end].strip().rstrip(",.")

        return name, cargo, location

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clean_google_redirect(self, href: str) -> Optional[str]:
        """Remove redirecionadores do Google e retorna a URL final do LinkedIn."""
        # Forma: /url?q=https://linkedin.com/in/...
        match = re.search(r'/url\?q=(https?://[^&]+)', href)
        if match:
            from urllib.parse import unquote
            return unquote(match.group(1))
        # Já é URL direta
        if href.startswith("https://linkedin.com") or href.startswith("https://www.linkedin.com"):
            return href
        return None

    def _is_valid_linkedin_profile(self, url: str) -> bool:
        """Valida que a URL é um perfil LinkedIn individual (não empresa)."""
        if not url:
            return False
        # Aceitar apenas perfis /in/ — rejeitar /company/, /jobs/, etc.
        return bool(re.search(r'linkedin\.com/in/[^/\s]+', url))

    def _classify_contact_type(self, title: str) -> str:
        """Determina o tipo de contato a partir do cargo extraído."""
        lower = title.lower()
        priority_map = [
            ("talent acquisition partner", "Talent Acquisition Partner"),
            ("talent acquisition", "Talent Acquisition"),
            ("tech recruiter", "Tech Recruiter"),
            ("it recruiter", "IT Recruiter"),
            ("data recruiter", "Data Recruiter"),
            ("recruiter", "Recruiter"),
            ("recrutador", "Recrutador"),
            ("people & talent", "People & Talent"),
            ("people and talent", "People & Talent"),
            ("hrbp", "HRBP"),
            ("recursos humanos", "Recursos Humanos"),
            (" rh ", "RH"),
        ]
        for key, label in priority_map:
            if key in lower:
                return label
        return "RH / People"

    def _calc_recruiter_priority(self, contact_type: str, location: str) -> str:
        """Atribui prioridade ao contato com base no cargo e localidade."""
        high_types = {"Talent Acquisition Partner", "Tech Recruiter", "IT Recruiter",
                      "Data Recruiter", "Talent Acquisition"}
        if contact_type in high_types:
            return "Alta"
        campinas_area = any(
            city in location
            for city in ["Campinas", "Paulínia", "Sumaré", "Hortolândia", "Valinhos"]
        )
        if campinas_area:
            return "Alta"
        return "Média"

    def _polite_sleep(self, min_sec: float = 3.0, max_sec: float = 7.0) -> None:
        """Pausa aleatória para evitar rate limiting."""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"    💤 Aguardando {delay:.1f}s...")
        time.sleep(delay)

"""Módulo de Deduplicação, Sanitização de URLs e Hashing Canônico."""

import re
import hashlib
import unicodedata
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class DeduplicationEngine:
    """Responsável por normalizar textos, URLs e gerar hashes canônicos de vagas."""

    # Parâmetros de rastreamento comumente anexados a links de vagas (mantendo identificadores reais como jk)
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "refid", "trackingid", "position", "pagenum", "trk",
        "fbclid", "gclid", "source", "originalsubdomain", "midtoken", "ebp",
        "ref", "f", "from", "vjs", "tk", "advn"
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        """Remove acentos, caracteres especiais e espaços extras para comparação uniforme."""
        if not text:
            return ""
        # Remove acentos
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        # Minúsculas
        text = text.lower()
        # Remove caracteres que não sejam letras, números ou espaços
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Remove espaços repetidos
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """Remove parâmetros de rastreamento de URLs para manter a URL limpa e canônica."""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
            filtered_query = [
                (k, v) for k, v in query_pairs 
                if k.lower() not in cls.TRACKING_PARAMS
            ]
            clean_query = urlencode(filtered_query)
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),
                parsed.params,
                clean_query,
                "" # remove fragment
            ))
            return clean_url
        except Exception:
            return url.strip()

    @classmethod
    def generate_job_hash(cls, empresa: str, titulo: str, localizacao: str, url: str = "") -> str:
        """Gera um hash SHA-256 estável para a vaga baseado em dados normalizados ou ID da URL."""
        # Se for LinkedIn, tentar extrair o ID numérico nativo
        if "linkedin.com" in url:
            match = re.search(r'view/(\d+)', url) or re.search(r'currentJobId=(\d+)', url) or re.search(r'-(\d+)\?', url)
            if match:
                return f"li_{match.group(1)}"

        # Se for Indeed, tentar extrair jk
        if "indeed.com" in url:
            match = re.search(r'jk=([a-zA-Z0-9]+)', url)
            if match:
                return f"in_{match.group(1)}"

        norm_empresa = cls.normalize_text(empresa)
        norm_titulo = cls.normalize_text(titulo)
        norm_local = cls.normalize_text(localizacao)

        # Chave composta estável
        composite_key = f"{norm_empresa}_{norm_titulo}_{norm_local}"
        return hashlib.sha256(composite_key.encode('utf-8')).hexdigest()

"""Recruiter collector agent.

This module provides a simple function to collect public recruiter profiles
associated with a hiring company. It does **not** modify the database or the
Excel sheet directly – it only returns a list of dictionaries that can be
merged by the caller (e.g. :class:`ExcelExporter`).

The implementation uses a lightweight HTTP request to the public LinkedIn
"People" page of a company and parses the resulting HTML with ``BeautifulSoup``.
If the request fails (rate‑limit, missing page, no internet, etc.) an empty list
is returned and the error is logged – the pipeline must continue without
interrupting the vacancy import.

The function is deliberately defensive because LinkedIn may block automated
scraping; it only extracts data that is openly visible without authentication.

Expected output format (list of dicts)::

    {
        "empresa": "Acme Corp",
        "vaga_relacionada": "Analista de Dados",
        "nome": "João Silva",
        "cargo": "Talent Acquisition Partner",
        "localidade": "São Paulo, SP",
        "tipo_contato": "LinkedIn",
        "linkedin_url": "https://www.linkedin.com/in/joaosilva",
        "mapeado_em": "2026-10-14",
        "prioridade": "Alta"
    }

The caller can decide how to compute ``prioridade`` (e.g. based on the vacancy
score).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

# Basic logging – the main pipeline config already sets a logger named
# ``RadarDeVagas``; we use a child logger for consistency.
logger = logging.getLogger("RadarDeVagas.RecruiterCollector")

# Titles that indicate a recruiter. The list is not exhaustive but covers the
# most common variations used in the original user request.
RECRUITER_TITLES = [
    "Talent Acquisition",
    "Recruiter",
    "Tech Recruiter",
    "IT Recruiter",
    "Data Recruiter",
    "Talent Acquisition Partner",
    "People & Talent",
    "Recruitment",
    "Recursos Humanos",
]


def _is_recruiter_title(title: str) -> bool:
    """Return ``True`` if *title* contains any of the recruiter keywords.

    Matching is case‑insensitive and uses a simple ``in`` check.
    """
    lower = title.lower()
    return any(keyword.lower() in lower for keyword in RECRUITER_TITLES)


def _extract_company_slug(url: str) -> str | None:
    """Extract the LinkedIn company slug from a vacancy URL.

    Example::

        https://www.linkedin.com/jobs/view/1234567890/ -> "company-name"

    The function looks for ``/company/`` in the URL; if not found it returns
    ``None`` because we cannot safely build the people page.
    """
    # Many vacancy URLs embed the company name after ``/company/``
    # e.g. ``.../company/acme-corp/...``. We split on that pattern.
    try:
        parts = url.split("/company/")
        if len(parts) < 2:
            return None
        slug_part = parts[1]
        # The slug is the first path segment after the split
        slug = slug_part.split("/")[0]
        return slug
    except Exception as exc:  # pragma: no cover – defensive
        logger.debug("Failed to extract company slug from %s: %s", url, exc)
        return None


def collect_recruiters(job: Any) -> List[Dict[str, Any]]:
    """Collect public recruiter profiles for *job*.

    Parameters
    ----------
    job: Any
        An object with at least ``empresa``, ``titulo`` and ``url`` attributes.
        It is typically a :class:`~src.core.models.JobOpportunity` instance.

    Returns
    -------
    List[Dict[str, Any]]
        A list of recruiter dictionaries ready to be merged into the
        ``👥 Recrutadores`` sheet.
    """
    recruiters: List[Dict[str, Any]] = []

    # Try to obtain a company identifier from the vacancy URL. If we cannot, we
    # simply skip collection – the alternative would be a direct LinkedIn search
    # which may trigger stricter rate‑limits.
    slug = _extract_company_slug(job.url)
    if not slug:
        logger.debug("No company slug found for %s; skipping recruiter search", job.url)
        return recruiters

    people_url = f"https://www.linkedin.com/company/{slug}/people/"
    logger.debug("Fetching recruiters from %s", people_url)

    try:
        response = requests.get(people_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200:
            logger.warning("LinkedIn people page returned status %s for %s", response.status_code, people_url)
            return recruiters
        soup = BeautifulSoup(response.text, "html.parser")
        # The public page lists profiles in <a> tags with href to the profile and a
        # sibling element containing the headline. The exact structure can vary;
        # we perform a best‑effort search.
        profile_cards = soup.select("a[data-control-name='people_profile']")
        for card in profile_cards:
            profile_url = card.get("href")
            # The headline is often inside a <p> or <span> with a class that
            # contains the word "headline". We look for the closest text that
            # resembles a title.
            parent = card.parent
            title_elem = parent.find(string=True, recursive=True)
            title = title_elem.strip() if title_elem else ""
            if not profile_url or not title:
                continue
            if _is_recruiter_title(title):
                recruiters.append(
                    {
                        "empresa": job.empresa,
                        "vaga_relacionada": job.titulo,
                        "nome": card.get_text(strip=True),  # name appears in the anchor text
                        "cargo": title,
                        "localidade": "",
                        "tipo_contato": "LinkedIn",
                        "linkedin_url": profile_url,
                        "mapeado_em": datetime.now().strftime("%Y-%m-%d"),
                        # Simple priority heuristic: high score -> Alta
                        "prioridade": "Alta" if getattr(job, "score", 0) >= 80 else "Média",
                    }
                )
    except requests.RequestException as exc:
        logger.warning("Error fetching recruiters for %s: %s", slug, exc)
    except Exception as exc:  # pragma: no cover – unexpected errors
        logger.exception("Unexpected error during recruiter collection: %s", exc)

    return recruiters

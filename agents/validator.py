# agents/validator.py
"""Validator Agent
===================

Este módulo implementa o **AGENTE VALIDADOR** responsável por:

1. Detectar vagas duplicadas na planilha ou no banco SQLite.
2. Detectar links inválidos (HTTP status != 200).
3. Detectar vagas encerradas (quando a página devolve 404 ou contém indicadores de "vaga encerrada").
4. Verificar se a vaga realmente corresponde ao cargo procurado (usando os termos de `config/cargos.yaml`).
5. Identificar a **modalidade** (Remoto / Híbrido / Presencial).
6. Identificar requisitos técnicos a partir da descrição da vaga.
7. Comparar requisitos com o perfil da candidata (arquivo `config/perfil_candidata.md`).
8. Recalcular a aderência (score) segundo a nova pontuação especificada.
9. Classificar a prioridade (ALTA, MÉDIA, BAIXA).

O agente devolve uma lista de objetos ``JobOpportunity`` já atualizados com os campos:

* ``score`` – pontuação entre 0 e 100.
* ``classificacao`` – string com a classificação de prioridade.
* ``modalidade`` – "Remoto", "Híbrido" ou "Presencial".
* ``requisitos_identificados`` – lista de requisitos técnicos extraídos.

A lógica de pontuação segue exatamente as regras fornecidas:

* **Peso base** (soma dos itens abaixo, limitado a 100):
  * +20 Dados/BI/Analytics
  * +15 Power BI
  * +15 SQL
  * +10 Excel
  * +10 Indicadores
  * +10 Experiência corporativa
  * +10 SAP/ERP
  * +10 Experiência em Operações/Comercial/Logística
* **Bônus**
  * +10 remoto
  * +5 híbrido (quando a cidade está na região de Campinas listada em `config/localizacao.yaml`)
* **Penalizações**
  * -20 quando a vaga exige experiência técnica incompatível com nível júnior.
  * -20 quando a vaga exige programação avançada como requisito principal.
  * -15 quando a vaga exige experiência muito distante do perfil.

A pontuação final é truncada entre 0 e 100.

---

## Estrutura do módulo

* ``CandidateProfile`` – carrega palavras‑chave do perfil da candidata.
* ``ValidatorAgent`` – classe principal com método ``validate_jobs`` que recebe
  a lista de vagas recém‑coletadas e devolve a lista validada.
* Funções auxiliares para cada responsabilidade listada acima.

---

```python
import logging
import re
from pathlib import Path
from typing import List, Set

import requests
from bs4 import BeautifulSoup

from src.core.models import JobOpportunity
from src.core.deduplication import DeduplicationEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modelo de perfil da candidata (extracted from config/perfil_candidata.md)
# ---------------------------------------------------------------------------
class CandidateProfile:
    def __init__(self) -> None:
        self.tech_keywords: Set[str] = {
            "power bi",
            "sql",
            "excel",
            "indicadores",
            "kpi",
            "sap",
            "erp",
            "logística",
            "operações",
            "comercial",
            "dados",
            "bi",
            "analytics",
        }
        self.accepted_remote: bool = True
        self.accepted_hybrid_cities: Set[str] = {
            "campinas",
            "valinhos",
            "vinhedo",
            "hortolândia",
            "sumaré",
            "paulínia",
            "indaiatuba",
            "americana",
        }

    def matches_requirement(self, requirement: str) -> bool:
        return any(kw in requirement.lower() for kw in self.tech_keywords)

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def is_duplicate(job: JobOpportunity, existing_hashes: Set[str]) -> bool:
    job_hash = job.id or DeduplicationEngine.generate_job_hash(
        job.empresa, job.titulo, job.localizacao, job.url
    )
    return job_hash in existing_hashes

def is_link_valid(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        return resp.status_code == 200
    except Exception as exc:
        logger.debug("Link inválido %s – %s", url, exc)
        return False

def is_job_closed(job: JobOpportunity) -> bool:
    try:
        resp = requests.get(job.url, timeout=5)
        if resp.status_code == 404:
            return True
        lowered = resp.text.lower()
        return any(phrase in lowered for phrase in [
            "vaga encerrada",
            "position not found",
            "vaga já preenchida",
        ])
    except Exception as exc:
        logger.debug("Erro ao checar vaga %s – %s", job.url, exc)
        return False

def matches_cargo(job: JobOpportunity, cargo_terms: List[str]) -> bool:
    title = job.titulo.lower()
    return any(term.lower() in title for term in cargo_terms)

def identify_modality(job: JobOpportunity) -> str:
    txt = " ".join(filter(None, [job.modalidade, job.localizacao, job.descricao])).lower()
    if "remoto" in txt:
        return "Remoto"
    if "híbrido" in txt or "hibrido" in txt:
        return "Híbrido"
    return "Presencial"

def extract_requirements(job: JobOpportunity) -> Set[str]:
    if not job.descricao:
        return set()
    soup = BeautifulSoup(job.descricao, "html.parser")
    plain = soup.get_text(separator=" ").lower()
    keywords = [
        "power bi",
        "sql",
        "excel",
        "kpi",
        "indicadores",
        "sap",
        "erp",
        "logística",
        "operações",
        "comercial",
        "python",
        "java",
        "programação",
        "desenvolvimento",
    ]
    return {kw for kw in keywords if kw in plain}

def compare_requirements(profile: CandidateProfile, requirements: Set[str]) -> int:
    # Map de requisitos → peso
    peso_map = {
        "dados": 20,
        "bi": 20,
        "analytics": 20,
        "power bi": 15,
        "sql": 15,
        "excel": 10,
        "indicadores": 10,
        "kpi": 10,
        "experiência corporativa": 10,
        "sap": 10,
        "erp": 10,
        "logística": 10,
        "operações": 10,
        "comercial": 10,
    }
    score = 0
    for req in requirements:
        key = None
        if req in {"dados", "bi", "analytics"}:
            key = "dados"
        elif req == "power bi":
            key = "power bi"
        elif req == "sql":
            key = "sql"
        elif req == "excel":
            key = "excel"
        elif req in {"indicadores", "kpi"}:
            key = "indicadores"
        elif req in {"sap", "erp"}:
            key = "sap"
        elif req == "logística":
            key = "logística"
        elif req == "operações":
            key = "operações"
        elif req == "comercial":
            key = "comercial"
        if key and key in peso_map:
            score += peso_map[key]
    return score

def apply_bonus(job: JobOpportunity, profile: CandidateProfile) -> int:
    modality = identify_modality(job)
    if modality == "Remoto":
        return 10
    if modality == "Híbrido":
        city = (job.localizacao or "").lower()
        if any(c in city for c in profile.accepted_hybrid_cities):
            return 5
    return 0

def apply_penalties(job: JobOpportunity) -> int:
    penalties = 0
    title = job.titulo.lower()
    desc = (job.descricao or "").lower()
    if any(level in title for level in ["senior", "pleno", "expert"]):
        penalties += 20
    prog_keywords = ["python", "java", "c++", "c#", "javascript", "nodejs", "programação avançada"]
    if any(kw in desc[:150] for kw in prog_keywords):
        penalties += 20
    distant = ["cloud", "devops", "machine learning", "data science", "big data"]
    if any(word in desc for word in distant):
        penalties += 15
    return penalties

def calculate_final_score(base: int, bonus: int, penalty: int) -> int:
    return max(0, min(100, base + bonus - penalty))

def classify_priority(score: int) -> str:
    if score >= 80:
        return "ALTA"
    if score >= 60:
        return "MÉDIA"
    return "BAIXA"

# ---------------------------------------------------------------------------
# Classe principal do agente
# ---------------------------------------------------------------------------
class ValidatorAgent:
    def __init__(self) -> None:
        self.profile = CandidateProfile()
        cargos_path = Path("config/cargos.yaml")
        import yaml
        if cargos_path.exists():
            with cargos_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            self.cargo_terms = cfg.get("prioridade_alta", []) + cfg.get("prioridade_media", [])
        else:
            self.cargo_terms = []
        self.seen_hashes: Set[str] = set()
        self.deduper = DeduplicationEngine()

    def _populate_seen_hashes(self, existing_jobs: List[JobOpportunity]) -> None:
        for job in existing_jobs:
            job_hash = job.id or DeduplicationEngine.generate_job_hash(
                job.empresa, job.titulo, job.localizacao, job.url
            )
            self.seen_hashes.add(job_hash)

    def validate_jobs(self, jobs: List[JobOpportunity], existing_jobs: List[JobOpportunity]) -> List[JobOpportunity]:
        self._populate_seen_hashes(existing_jobs)
        validated: List[JobOpportunity] = []
        for job in jobs:
            # 1 – Duplicidade
            if is_duplicate(job, self.seen_hashes):
                logger.debug("Vaga duplicada descartada: %s", job.url)
                continue
            # 2 – Link válido
            if not is_link_valid(job.url):
                logger.debug("Link inválido descartado: %s", job.url)
                continue
            # 3 – Vaga encerrada
            if is_job_closed(job):
                logger.debug("Vaga encerrada descartada: %s", job.url)
                continue
            # 4 – Correspondência de cargo
            if not matches_cargo(job, self.cargo_terms):
                logger.debug("Cargo não corresponde: %s", job.titulo)
                continue
            # 5 – Modalidade
            job.modalidade = identify_modality(job)
            # 6 – Requisitos técnicos
            requisitos = extract_requirements(job)
            job.requisitos_identificados = list(requisitos)
            # 7 – Comparar requisitos com perfil
            base_score = compare_requirements(self.profile, requisitos)
            # 8 – Bonificação e penalizações
            bonus = apply_bonus(job, self.profile)
            penalty = apply_penalties(job)
            job.score = calculate_final_score(base_score, bonus, penalty)
            # 9 – Classificação
            job.classificacao = classify_priority(job.score)
            # Atualiza hash para evitar re‑inserção
            job.id = DeduplicationEngine.generate_job_hash(
                job.empresa, job.titulo, job.localizacao, job.url
            )
            self.seen_hashes.add(job.id)
            validated.append(job)
        return validated

__all__ = ["ValidatorAgent"]
```

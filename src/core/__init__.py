"""Módulos centrais de persistência, modelos, deduplicação e pontuação."""

from .models import JobOpportunity, FitScoreResult
from .database import DatabaseManager
from .deduplication import DeduplicationEngine
from .scorer import FitScorer

__all__ = [
    "JobOpportunity",
    "FitScoreResult",
    "DatabaseManager",
    "DeduplicationEngine",
    "FitScorer",
]

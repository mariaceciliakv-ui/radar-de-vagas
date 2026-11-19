"""Gerenciador de Banco de Dados Local SQLite para Histórico e Deduplicação."""

import sqlite3
import os
from typing import List, Optional, Set
from .models import JobOpportunity


class DatabaseManager:
    """Controla a persistência local em SQLite para evitar reprocessamento e duplicatas."""

    def __init__(self, db_path: str = "data/job_vault.db"):
        self.db_path = db_path
        self._conn = None
        parent_dir = os.path.dirname(self.db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if self.db_path == ":memory:":
            self._conn = sqlite3.connect(":memory:")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Cria as tabelas caso não existam."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_hash TEXT PRIMARY KEY,
                    titulo TEXT,
                    empresa TEXT,
                    localizacao TEXT,
                    modalidade TEXT,
                    salario TEXT,
                    url TEXT UNIQUE,
                    fonte TEXT,
                    score REAL,
                    classificacao TEXT,
                    coletado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_seen_jobs_url ON seen_jobs(url);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_seen_jobs_score ON seen_jobs(score);
            """)
            conn.commit()

    def is_job_seen(self, job_hash: str, url: str) -> bool:
        """Verifica se a vaga já foi registrada anteriormente por hash ou URL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM seen_jobs 
                WHERE job_hash = ? OR url = ?
                LIMIT 1
            """, (job_hash, url))
            return cursor.fetchone() is not None

    def get_all_seen_hashes(self) -> Set[str]:
        """Retorna todos os hashes de vagas já vistas para filtragem rápida em memória."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job_hash FROM seen_jobs")
            return {row[0] for row in cursor.fetchall()}

    def save_job(self, job: JobOpportunity) -> bool:
        """Salva uma nova vaga no banco de dados. Retorna True se for inserção nova."""
        if not job.id:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO seen_jobs (
                        job_hash, titulo, empresa, localizacao, modalidade, 
                        salario, url, fonte, score, classificacao, coletado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id, job.titulo, job.empresa, job.localizacao, job.modalidade,
                    job.salario, job.url, job.fonte, job.score, job.classificacao, job.coletado_em
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_jobs_batch(self, jobs: List[JobOpportunity]) -> int:
        """Salva uma lista de vagas em lote. Retorna o número de novas vagas inseridas."""
        inserted_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for job in jobs:
                if not job.id:
                    continue
                try:
                    cursor.execute("""
                        INSERT INTO seen_jobs (
                            job_hash, titulo, empresa, localizacao, modalidade, 
                            salario, url, fonte, score, classificacao, coletado_em
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job.id, job.titulo, job.empresa, job.localizacao, job.modalidade,
                        job.salario, job.url, job.fonte, job.score, job.classificacao, job.coletado_em
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    continue
            conn.commit()
        return inserted_count

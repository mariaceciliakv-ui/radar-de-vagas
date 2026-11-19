"""Convenient CLI entry point for the Radar de Vagas.

The original script is ``run_radar.py`` which offers several command line flags.
For everyday usage the user wants a short command named ``Buscar vagas``.
This wrapper simply forwards to :func:`run_radar.execute_radar_sync` with a
reasonable default configuration (max 8 queries, 30 results per query) and
exposes the most common options via ``--incremental`` and ``--reset-db``.

Usage examples::

    python buscar_vagas.py                     # run a full radar search
    python buscar_vagas.py --incremental      # only fetch new vacancies (no DB reset)
    python buscar_vagas.py --reset-db          # start from an empty SQLite DB

The script deliberately avoids any heavy‑weight argument parsing – it mirrors
the options of ``run_radar.py`` so that existing behaviour is preserved.
"""

import argparse
from run_radar import execute_radar_sync

def main() -> None:
    parser = argparse.ArgumentParser(description="Buscar vagas – wrapper around run_radar")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Apaga o banco SQLite antes de executar (reavalia vagas já vistas).",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Executa a busca incremental (mesmo que --reset-db=False).",
    )
    # The wrapper uses the same defaults as run_radar.py but allows the user to
    # override the limit if desired.
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Número máximo de resultados por consulta (padrão: 30).",
    )
    args = parser.parse_args()

    # ``incremental`` is just a semantic alias for not resetting the DB.
    reset = args.reset_db
    execute_radar_sync(max_queries=8, limit_results=args.limit, reset_db=reset)

if __name__ == "__main__":
    main()

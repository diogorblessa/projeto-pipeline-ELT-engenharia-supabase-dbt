#!/usr/bin/env bash
# Pipeline ELT completo: Extract+Load -> Transform.
# Uso: ./scripts/run-pipeline.sh
# Para Docker: docker compose run --rm extract && docker compose run --rm dbt run
set -euo pipefail
uv run --package extract_load python -m extract_load
uv run --package transform python -c "from dotenv import load_dotenv; load_dotenv('.env'); from dbt.cli.main import dbtRunner; import sys; sys.exit(0 if dbtRunner().invoke(['run','--project-dir','transform','--profiles-dir','transform']).success else 1)"

#!/bin/sh
set -e

echo "[entrypoint] Aguardando o PostgreSQL ficar disponivel..."
python - <<'PY'
import sys, time
from sqlalchemy import create_engine, text
from src.config import settings

url = settings.database_url
if not url:
    print("[entrypoint] DATABASE_URL nao definida.", file=sys.stderr)
    sys.exit(1)

for _ in range(60):
    try:
        with create_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] PostgreSQL pronto.")
        break
    except Exception as erro:
        print(f"[entrypoint] PostgreSQL indisponivel ({erro}); nova tentativa em 2s...")
        time.sleep(2)
else:
    print("[entrypoint] Timeout aguardando o PostgreSQL.", file=sys.stderr)
    sys.exit(1)
PY

echo "[entrypoint] Aplicando migracoes (alembic upgrade head)..."
alembic upgrade head

if [ "${ENV:-dev}" = "dev" ] && [ "${SEED_ON_STARTUP:-true}" = "true" ]; then
    echo "[entrypoint] Seed de perfis mock (dev)..."
    python -m scripts.seed || echo "[entrypoint] Seed falhou (ignorado)."
fi

echo "[entrypoint] Subindo a API na porta ${PORT:-8000}..."
exec uvicorn src.controllers.api:app --host 0.0.0.0 --port "${PORT:-8000}"

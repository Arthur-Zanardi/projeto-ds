"""Fixtures de teste: banco PostgreSQL + autenticação JWT.

Os testes de banco usam a `DATABASE_URL` do ambiente (no CI, um Postgres com
pgvector). Sem banco acessível, são ignorados (skip) em vez de falhar.
"""
import os

# Defaults de teste — definidos ANTES de importar src.config.
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("SEED_ON_STARTUP", "false")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL", "")

TABELAS = [
    "mensagens_conversa",
    "matches_usuario",
    "conversas_match",
    "acoes_match",
    "vetores_salvos",
    "logs_api",
    "historico_chat",
    "perfis_publicos",
    "perfis_vetoriais",
    "usuarios",
]


@pytest.fixture(scope="session")
def _schema():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL nao definida; testes de banco ignorados.")
    from src.services.db import get_engine

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as erro:  # pragma: no cover
        pytest.skip(f"Postgres indisponivel: {erro}")

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture
def db(_schema):
    from src.services.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE " + ", ".join(TABELAS) + " RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient

    from src.controllers import api

    with TestClient(api.app) as cliente:
        yield cliente


@pytest.fixture
def auth(client):
    def _auth(email, senha="senha123", nome=None):
        client.post("/auth/register", json={"email": email, "senha": senha, "nome": nome})
        resp = client.post("/auth/login", json={"email": email, "senha": senha})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth

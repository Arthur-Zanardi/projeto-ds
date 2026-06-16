"""Engine SQLAlchemy, pool de conexões e gestão de sessões.

A criação do engine é preguiçosa para que importar este módulo não exija
`DATABASE_URL` (ex.: processo do frontend). O esquema é criado/evoluído
apenas via Alembic — nunca em runtime por request.
"""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL não configurada.")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            future=True,
        )
    return _engine


def get_sessionmaker() -> "sessionmaker[Session]":
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sessão transacional: commit no sucesso, rollback em erro, sempre fecha."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """Dependency do FastAPI: uma sessão por request."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verificar_conexao() -> bool:
    """Usado pelo health check: SELECT 1."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True

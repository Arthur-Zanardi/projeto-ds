"""Migração (opcional) dos dados locais SQLite/Chroma -> PostgreSQL/pgvector.

Lê o antigo `banco_relacional.db` (SQLite) e, se possível, o `banco_vetorial`
(ChromaDB) e transfere os dados para o Postgres configurado em DATABASE_URL.
É best-effort e idempotente o suficiente para rodar mais de uma vez.

Uso:
    python -m scripts.migrar_sqlite_para_postgres \
        --sqlite ./banco_relacional.db --chroma ./banco_vetorial

Pré-requisito: o esquema Postgres já criado (alembic upgrade head).
"""
import argparse
import json
import logging
import sqlite3
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db_models import (
    AcaoMatch,
    ConversaMatch,
    HistoricoChat,
    LogApi,
    MatchUsuario,
    MensagemConversa,
    PerfilPublico,
    Usuario,
    VetorSalvo,
)
from src.services.db import session_scope

logger = logging.getLogger(__name__)


def _linhas(conn: sqlite3.Connection, tabela: str):
    try:
        conn.row_factory = sqlite3.Row
        return conn.execute(f"SELECT * FROM {tabela}").fetchall()
    except sqlite3.Error as erro:
        logger.warning("Tabela %s indisponivel no SQLite: %s", tabela, erro)
        return []


def _jsonb(valor):
    if valor in (None, ""):
        return None
    try:
        return json.loads(valor)
    except (TypeError, json.JSONDecodeError):
        return None


def migrar_relacional(sqlite_path: str) -> None:
    conn = sqlite3.connect(sqlite_path)
    with session_scope() as s:
        for row in _linhas(conn, "usuarios"):
            s.execute(
                pg_insert(Usuario)
                .values(nome=row["nome"], email=str(row["email"]).strip().lower(),
                        senha_hash=row["senha_hash"])
                .on_conflict_do_nothing(index_elements=["email"])
            )
        for row in _linhas(conn, "perfis_publicos"):
            s.execute(
                pg_insert(PerfilPublico)
                .values(
                    usuario=row["usuario"], nome=row["nome"], idade=row["idade"],
                    foto_url=row["foto_url"], descricao=row["descricao"],
                    localizacao=row["localizacao"], cargo=row["cargo"],
                    origem=row["origem"], mock_customizado=bool(row["mock_customizado"]),
                )
                .on_conflict_do_nothing(index_elements=["usuario"])
            )
        for row in _linhas(conn, "conversas_match"):
            s.execute(
                pg_insert(ConversaMatch)
                .values(
                    conversa_id=row["conversa_id"], participante_1=row["participante_1"],
                    participante_2=row["participante_2"], tipo=row["tipo"],
                )
                .on_conflict_do_nothing(index_elements=["conversa_id"])
            )
        for row in _linhas(conn, "matches_usuario"):
            s.execute(
                pg_insert(MatchUsuario)
                .values(
                    usuario=row["usuario"], match_id=row["match_id"], nome=row["nome"],
                    afinidade=row["afinidade"], dados_match=_jsonb(row["dados_match_json"]),
                    conversa_id=row["conversa_id"],
                )
                .on_conflict_do_nothing(index_elements=["usuario", "match_id"])
            )
        # mensagens: a tabela legada mensagens_conversa ja existe; mensagens_match
        # legada (se houver) e convertida para mensagens_conversa.
        for row in _linhas(conn, "mensagens_conversa"):
            s.add(MensagemConversa(
                conversa_id=row["conversa_id"], remetente=row["remetente"],
                mensagem=row["mensagem"],
            ))
        for row in _linhas(conn, "historico_chat"):
            s.add(HistoricoChat(
                usuario=row["usuario"], remetente=row["remetente"], mensagem=row["mensagem"],
            ))
        for row in _linhas(conn, "acoes_match"):
            s.execute(
                pg_insert(AcaoMatch)
                .values(usuario=row["usuario"], candidato_id=row["candidato_id"], acao=row["acao"])
                .on_conflict_do_nothing(index_elements=["usuario", "candidato_id"])
            )
        for row in _linhas(conn, "vetores_salvos"):
            s.add(VetorSalvo(usuario=row["usuario"], vetores_json=_jsonb(row["vetores_json"]) or {}))
        for row in _linhas(conn, "logs_api"):
            s.add(LogApi(
                usuario=row["usuario"], endpoint=row["endpoint"], acao=row["acao"],
                status=row["status"], mensagem=row["mensagem"],
                detalhes_json=_jsonb(row["detalhes_json"]),
            ))
    conn.close()
    logger.info("Migracao relacional concluida.")


def migrar_vetorial(chroma_path: str) -> None:
    if not Path(chroma_path).exists():
        logger.warning("Diretorio Chroma '%s' nao encontrado; pulando vetores.", chroma_path)
        return
    try:
        import chromadb
    except ImportError:
        logger.warning("chromadb nao instalado; pulando migracao vetorial.")
        return

    from src.models.db_models import VECTOR_DIM
    from src.services.database import _upsert_embedding

    client = chromadb.PersistentClient(path=chroma_path)
    colecao = client.get_or_create_collection(name="perfis_matchai")
    dados = colecao.get(include=["embeddings", "metadatas"])
    ids = dados.get("ids", []) or []
    embeddings = dados.get("embeddings", []) or []
    metadados = dados.get("metadatas", []) or []
    migrados = 0
    for indice, id_usuario in enumerate(ids):
        if indice >= len(embeddings):
            continue
        vetor = [float(v) for v in embeddings[indice]]
        if len(vetor) != VECTOR_DIM:
            logger.warning("Vetor de %s tem %d dims (!= %d); pulando.", id_usuario, len(vetor), VECTOR_DIM)
            continue
        meta = metadados[indice] if indice < len(metadados) else {}
        nome = (meta or {}).get("nome", id_usuario)
        _upsert_embedding(id_usuario, nome, vetor)
        migrados += 1
    logger.info("Migracao vetorial concluida (%d perfis).", migrados)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra SQLite/Chroma -> Postgres/pgvector")
    parser.add_argument("--sqlite", default="./banco_relacional.db")
    parser.add_argument("--chroma", default="./banco_vetorial")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if Path(args.sqlite).exists():
        migrar_relacional(args.sqlite)
    else:
        logger.warning("SQLite '%s' nao encontrado; pulando relacional.", args.sqlite)
    migrar_vetorial(args.chroma)


if __name__ == "__main__":
    main()

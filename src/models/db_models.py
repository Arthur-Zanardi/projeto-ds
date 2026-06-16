"""Modelos SQLAlchemy (PostgreSQL + pgvector).

Espelham as tabelas legadas do SQLite usando tipos nativos do Postgres:
IDENTITY para PKs, TIMESTAMP WITH TIME ZONE com default no servidor,
JSONB no lugar de TEXT-JSON, BOOLEAN no lugar de 0/1 e CHECK constraints.
A tabela `mensagens_match` legada foi consolidada em `mensagens_conversa`.
"""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Dimensão do embedding = psicológico(7) + valores(6) + interesses(21).
# Mantida em sincronia com dimensoes_schema_vetorial() em services/database.py.
VECTOR_DIM = 34


class Base(DeclarativeBase):
    pass


def _coluna_data_hora() -> Mapped[datetime]:
    return mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = _coluna_data_hora()


class PerfilPublico(Base):
    __tablename__ = "perfis_publicos"

    usuario: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    idade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foto_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    localizacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    cargo: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str] = mapped_column(Text, nullable=False, server_default="real")
    mock_customizado: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    data_hora: Mapped[datetime] = _coluna_data_hora()

    __table_args__ = (Index("idx_perfis_publicos_origem", "origem"),)


class ConversaMatch(Base):
    __tablename__ = "conversas_match"

    conversa_id: Mapped[str] = mapped_column(Text, primary_key=True)
    participante_1: Mapped[str] = mapped_column(Text, nullable=False)
    participante_2: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False, server_default="real")
    data_hora: Mapped[datetime] = _coluna_data_hora()


class MatchUsuario(Base):
    __tablename__ = "matches_usuario"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False)
    match_id: Mapped[str] = mapped_column(Text, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    afinidade: Mapped[str | None] = mapped_column(Text, nullable=True)
    dados_match: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    data_hora: Mapped[datetime] = _coluna_data_hora()
    conversa_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("conversas_match.conversa_id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("usuario", "match_id", name="uq_matches_usuario_usuario_match"),
        Index("idx_matches_usuario_usuario", "usuario"),
    )


class MensagemConversa(Base):
    __tablename__ = "mensagens_conversa"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    conversa_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("conversas_match.conversa_id", ondelete="CASCADE"),
        nullable=False,
    )
    remetente: Mapped[str] = mapped_column(Text, nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    data_hora: Mapped[datetime] = _coluna_data_hora()

    __table_args__ = (Index("idx_mensagens_conversa_conversa", "conversa_id", "id"),)


class HistoricoChat(Base):
    __tablename__ = "historico_chat"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    remetente: Mapped[str] = mapped_column(Text, nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    data_hora: Mapped[datetime] = _coluna_data_hora()


class AcaoMatch(Base):
    __tablename__ = "acoes_match"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False)
    candidato_id: Mapped[str] = mapped_column(Text, nullable=False)
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    data_hora: Mapped[datetime] = _coluna_data_hora()

    __table_args__ = (
        UniqueConstraint("usuario", "candidato_id", name="uq_acoes_match_usuario_candidato"),
        CheckConstraint("acao IN ('like', 'pass')", name="ck_acoes_match_acao"),
        Index("idx_acoes_match_usuario", "usuario", "candidato_id"),
    )


class VetorSalvo(Base):
    __tablename__ = "vetores_salvos"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    vetores_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data_hora: Mapped[datetime] = _coluna_data_hora()


class LogApi(Base):
    __tablename__ = "logs_api"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    detalhes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    data_hora: Mapped[datetime] = _coluna_data_hora()


class PerfilVetorial(Base):
    __tablename__ = "perfis_vetoriais"

    usuario: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)

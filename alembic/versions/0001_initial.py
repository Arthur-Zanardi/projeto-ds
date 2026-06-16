"""esquema inicial: tabelas relacionais + pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VECTOR_DIM = 34


def _data_hora():
    return sa.Column(
        "data_hora",
        sa.TIMESTAMP(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    # Extensão pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "conversas_match",
        sa.Column("conversa_id", sa.Text(), primary_key=True),
        sa.Column("participante_1", sa.Text(), nullable=False),
        sa.Column("participante_2", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False, server_default="real"),
        _data_hora(),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    op.create_table(
        "perfis_publicos",
        sa.Column("usuario", sa.Text(), primary_key=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("idade", sa.Integer(), nullable=True),
        sa.Column("foto_url", sa.Text(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("localizacao", sa.Text(), nullable=True),
        sa.Column("cargo", sa.Text(), nullable=True),
        sa.Column("origem", sa.Text(), nullable=False, server_default="real"),
        sa.Column("mock_customizado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _data_hora(),
    )
    op.create_index("idx_perfis_publicos_origem", "perfis_publicos", ["origem"])

    op.create_table(
        "matches_usuario",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("match_id", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("afinidade", sa.Text(), nullable=True),
        sa.Column("dados_match", postgresql.JSONB(), nullable=True),
        _data_hora(),
        sa.Column("conversa_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversa_id"], ["conversas_match.conversa_id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("usuario", "match_id", name="uq_matches_usuario_usuario_match"),
    )
    op.create_index("idx_matches_usuario_usuario", "matches_usuario", ["usuario"])

    op.create_table(
        "mensagens_conversa",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("conversa_id", sa.Text(), nullable=False),
        sa.Column("remetente", sa.Text(), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        _data_hora(),
        sa.ForeignKeyConstraint(
            ["conversa_id"], ["conversas_match.conversa_id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_mensagens_conversa_conversa", "mensagens_conversa", ["conversa_id", "id"]
    )

    op.create_table(
        "historico_chat",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("remetente", sa.Text(), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        _data_hora(),
    )
    op.create_index("ix_historico_chat_usuario", "historico_chat", ["usuario"])

    op.create_table(
        "acoes_match",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("candidato_id", sa.Text(), nullable=False),
        sa.Column("acao", sa.Text(), nullable=False),
        _data_hora(),
        sa.UniqueConstraint("usuario", "candidato_id", name="uq_acoes_match_usuario_candidato"),
        sa.CheckConstraint("acao IN ('like', 'pass')", name="ck_acoes_match_acao"),
    )
    op.create_index("idx_acoes_match_usuario", "acoes_match", ["usuario", "candidato_id"])

    op.create_table(
        "vetores_salvos",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("vetores_json", postgresql.JSONB(), nullable=False),
        _data_hora(),
    )
    op.create_index("ix_vetores_salvos_usuario", "vetores_salvos", ["usuario"])

    op.create_table(
        "logs_api",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("acao", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("detalhes_json", postgresql.JSONB(), nullable=True),
        _data_hora(),
    )
    op.create_index("ix_logs_api_usuario", "logs_api", ["usuario"])

    op.create_table(
        "perfis_vetoriais",
        sa.Column("usuario", sa.Text(), primary_key=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(VECTOR_DIM), nullable=False),
    )
    # Índice HNSW com distância de cosseno (pgvector)
    op.execute(
        "CREATE INDEX idx_perfis_vetoriais_embedding "
        "ON perfis_vetoriais USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_perfis_vetoriais_embedding")
    op.drop_table("perfis_vetoriais")
    op.drop_index("ix_logs_api_usuario", table_name="logs_api")
    op.drop_table("logs_api")
    op.drop_index("ix_vetores_salvos_usuario", table_name="vetores_salvos")
    op.drop_table("vetores_salvos")
    op.drop_index("idx_acoes_match_usuario", table_name="acoes_match")
    op.drop_table("acoes_match")
    op.drop_index("ix_historico_chat_usuario", table_name="historico_chat")
    op.drop_table("historico_chat")
    op.drop_index("idx_mensagens_conversa_conversa", table_name="mensagens_conversa")
    op.drop_table("mensagens_conversa")
    op.drop_index("idx_matches_usuario_usuario", table_name="matches_usuario")
    op.drop_table("matches_usuario")
    op.drop_index("idx_perfis_publicos_origem", table_name="perfis_publicos")
    op.drop_table("perfis_publicos")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("conversas_match")

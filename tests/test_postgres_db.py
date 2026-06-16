"""Testes da camada de dados PostgreSQL."""
from src.services import postgres_db
from src.services.postgres_db import PostgresUserRepository


def test_criar_e_buscar_usuario(db):
    repo = PostgresUserRepository()
    assert repo.criar_usuario(email="Joao@Example.com", senha_pura="x") is True
    # e-mail normalizado (lowercase)
    usuario = repo.buscar_usuario_por_email("joao@example.com")
    assert usuario is not None
    assert usuario["email"] == "joao@example.com"
    # duplicado retorna False
    assert repo.criar_usuario(email="joao@example.com", senha_pura="y") is False


def test_salvar_e_obter_perfil_publico(db):
    salvo = postgres_db.salvar_perfil_publico(
        usuario="lia@example.com", nome="Lia", idade=21, localizacao="Recife"
    )
    assert salvo["nome"] == "Lia"
    assert salvo["idade"] == 21
    obtido = postgres_db.obter_perfil_publico("lia@example.com")
    assert obtido["localizacao"] == "Recife"


def test_acao_match_upsert(db):
    postgres_db.registrar_acao_match("u@example.com", "cand_1", "like")
    acao = postgres_db.obter_acao_match("u@example.com", "cand_1")
    assert acao["acao"] == "like"
    postgres_db.registrar_acao_match("u@example.com", "cand_1", "pass")
    assert postgres_db.obter_acao_match("u@example.com", "cand_1")["acao"] == "pass"


def test_match_e_mensagens(db):
    postgres_db.criar_match_usuario(
        usuario="u@example.com", match_id="user_maria", nome="Maria", tipo="mock"
    )
    matches = postgres_db.listar_matches_usuario("u@example.com")
    assert len(matches) == 1
    postgres_db.salvar_mensagem_match("u@example.com", "user_maria", "usuario", "Oi")
    historico = postgres_db.obter_historico_match("u@example.com", "user_maria")
    assert historico == [{"remetente": "usuario", "mensagem": "Oi"}]

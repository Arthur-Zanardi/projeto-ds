import json
import sqlite3

import pytest

from src.controllers.login_controller import LoginController
from src.services import sqlite_db


def test_iniciar_banco_sqlite_cria_tabelas(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    sqlite_db.iniciar_banco_sqlite()

    conn = sqlite3.connect(banco_teste)
    tabelas = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    conn.close()

    assert "historico_chat" in tabelas
    assert "matches_usuario" in tabelas
    assert "mensagens_match" in tabelas
    assert "vetores_salvos" in tabelas
    assert "logs_api" in tabelas
    assert "usuarios" in tabelas


def test_salvar_e_obter_historico_chat_em_ordem(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    sqlite_db.salvar_mensagem("user_teste", "usuario", "Oi")
    sqlite_db.salvar_mensagem("user_teste", "ia", "Tudo bem?")

    historico = sqlite_db.obter_historico_chat("user_teste")

    assert historico == [
        {"remetente": "usuario", "mensagem": "Oi"},
        {"remetente": "ia", "mensagem": "Tudo bem?"},
    ]


def test_criar_e_listar_matches_por_usuario(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    sqlite_db.criar_match_usuario(
        usuario="user_teste",
        match_id="user_maria",
        nome="Maria",
        afinidade="85%",
        dados_match={"idade": 27},
    )
    sqlite_db.criar_match_usuario(
        usuario="user_teste",
        match_id="user_joao",
        nome="Joao",
    )
    sqlite_db.criar_match_usuario(
        usuario="outro_usuario",
        match_id="user_ana",
        nome="Ana",
    )

    matches = sqlite_db.listar_matches_usuario("user_teste")

    assert [match["match_id"] for match in matches] == [
        "user_maria",
        "user_joao",
    ]
    assert matches[0]["usuario"] == "user_teste"
    assert matches[0]["nome"] == "Maria"
    assert matches[0]["afinidade"] == "85%"
    assert matches[0]["dados_match"] == {"idade": 27}
    assert matches[1]["dados_match"] is None


def test_criar_match_atualiza_registro_existente(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    primeiro = sqlite_db.criar_match_usuario(
        usuario="user_teste",
        match_id="user_maria",
        nome="Maria",
        afinidade="80%",
    )
    atualizado = sqlite_db.criar_match_usuario(
        usuario="user_teste",
        match_id="user_maria",
        nome="Maria Silva",
        afinidade="91%",
        dados_match={"cidade": "Recife"},
    )

    matches = sqlite_db.listar_matches_usuario("user_teste")

    assert primeiro["id"] == atualizado["id"]
    assert len(matches) == 1
    assert matches[0]["nome"] == "Maria Silva"
    assert matches[0]["afinidade"] == "91%"
    assert matches[0]["dados_match"] == {"cidade": "Recife"}


def test_salvar_e_obter_historico_match_isolado_por_conversa(
    tmp_path,
    monkeypatch,
):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    sqlite_db.criar_match_usuario("user_teste", "user_maria", "Maria")
    sqlite_db.criar_match_usuario("user_teste", "user_joao", "Joao")
    sqlite_db.salvar_mensagem_match(
        "user_teste",
        "user_maria",
        "usuario",
        "Oi, Maria",
    )
    sqlite_db.salvar_mensagem_match(
        "user_teste",
        "user_maria",
        "match",
        "Oi!",
    )
    sqlite_db.salvar_mensagem_match(
        "user_teste",
        "user_joao",
        "usuario",
        "Oi, Joao",
    )

    historico_maria = sqlite_db.obter_historico_match(
        "user_teste",
        "user_maria",
    )
    historico_joao = sqlite_db.obter_historico_match(
        "user_teste",
        "user_joao",
    )

    assert historico_maria == [
        {"remetente": "usuario", "mensagem": "Oi, Maria"},
        {"remetente": "match", "mensagem": "Oi!"},
    ]
    assert historico_joao == [
        {"remetente": "usuario", "mensagem": "Oi, Joao"},
    ]


def test_salvar_mensagem_match_inexistente_retorna_erro(
    tmp_path,
    monkeypatch,
):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    with pytest.raises(ValueError, match="Match nao encontrado."):
        sqlite_db.salvar_mensagem_match(
            "user_teste",
            "match_inexistente",
            "usuario",
            "Oi",
        )


def test_salvar_vetores_sqlite_guarda_json(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)
    vetores = {
        "psicologico": {"extroversao": 0.8},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 1.0},
    }

    sqlite_db.salvar_vetores_sqlite("user_teste", vetores)

    conn = sqlite3.connect(banco_teste)
    usuario, vetores_json = conn.execute(
        "SELECT usuario, vetores_json FROM vetores_salvos"
    ).fetchone()
    conn.close()

    assert usuario == "user_teste"
    assert json.loads(vetores_json) == vetores


def test_obter_ultimo_vetor_sqlite_retorna_vetor_mais_recente(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)
    primeiro_vetor = {
        "psicologico": {"extroversao": 0.3},
        "valores": {},
        "interesses": {},
    }
    segundo_vetor = {
        "psicologico": {"extroversao": 0.8},
        "valores": {},
        "interesses": {},
    }

    sqlite_db.salvar_vetores_sqlite("user_teste", primeiro_vetor)
    sqlite_db.salvar_vetores_sqlite("user_teste", segundo_vetor)

    assert sqlite_db.obter_ultimo_vetor_sqlite("user_teste") == segundo_vetor


def test_obter_ultimo_vetor_sqlite_retorna_none_sem_vetor(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    assert sqlite_db.obter_ultimo_vetor_sqlite("user_teste") is None


def test_salvar_e_obter_logs_api_em_ordem(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    sqlite_db.registrar_log_api(
        usuario="user_teste",
        endpoint="/chat",
        acao="receber_mensagem",
        status="iniciado",
        mensagem="Mensagem recebida.",
        detalhes={"texto_tamanho": 2},
    )
    sqlite_db.registrar_log_api(
        usuario="user_teste",
        endpoint="/chat",
        acao="responder_ia",
        status="sucesso",
        mensagem="Resposta gerada.",
    )

    logs = sqlite_db.obter_logs_api("user_teste")

    assert logs[0]["endpoint"] == "/chat"
    assert logs[0]["acao"] == "receber_mensagem"
    assert logs[0]["status"] == "iniciado"
    assert logs[0]["detalhes"] == {"texto_tamanho": 2}
    assert logs[1]["acao"] == "responder_ia"
    assert logs[1]["detalhes"] is None


def test_sqlite_user_repository_cria_e_autentica_usuario(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    repo = sqlite_db.SQLiteUserRepository()

    assert repo.criar_usuario("Ana", "ana@email.com", "segredo") is True
    assert repo.criar_usuario("Ana 2", "ana@email.com", "segredo") is False

    usuario = repo.buscar_usuario_por_email("ana@email.com")

    assert usuario["nome"] == "Ana"
    assert usuario["senha_hash"] != "segredo"

    controller = LoginController(repo)

    assert controller.realizar_login("ana@email.com", "segredo")["nome"] == "Ana"
    assert controller.realizar_login("ana@email.com", "senha-errada") is None

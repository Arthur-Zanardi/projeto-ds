import json
import sqlite3

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
    assert "vetores_salvos" in tabelas
    assert "logs_api" in tabelas


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

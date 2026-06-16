import json
import sqlite3

import pytest

from src.controllers.login_controller import LoginController
from src.services import sqlite_db


ADMIN_EMAIL = "rafaellapipucos@gmail.com"


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
    assert "perfis_publicos" in tabelas
    assert "acoes_match" in tabelas
    assert "conversas_match" in tabelas
    assert "mensagens_conversa" in tabelas
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


def test_perfil_publico_acao_e_match_confirmado_compartilham_conversa(
    tmp_path,
    monkeypatch,
):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    perfil_ana = sqlite_db.salvar_perfil_publico(
        usuario="ANA@EMAIL.COM",
        nome="Ana",
        idade="24",
        descricao="Perfil Ana",
        localizacao="Recife",
        cargo="Dev",
    )
    perfil_bia = sqlite_db.salvar_perfil_publico(
        usuario="bia@email.com",
        nome="Bia",
        idade=25,
        descricao="Perfil Bia",
        localizacao="Olinda",
        cargo="Designer",
    )

    assert perfil_ana["usuario"] == "ana@email.com"
    assert perfil_ana["idade"] == 24
    assert sqlite_db.registrar_acao_match(
        "ana@email.com",
        "bia@email.com",
        "like",
    )["acao"] == "like"

    sqlite_db.confirmar_match(
        usuario="ana@email.com",
        candidato_id="bia@email.com",
        perfil_candidato=perfil_bia,
        perfil_usuario=perfil_ana,
        tipo="real",
        sugestoes=[{"campo": "musica", "texto": "Oi"}],
    )
    sqlite_db.salvar_mensagem_match(
        "ana@email.com",
        "bia@email.com",
        "usuario",
        "Oi Bia",
    )

    assert sqlite_db.obter_historico_match("ana@email.com", "bia@email.com") == [
        {"remetente": "usuario", "mensagem": "Oi Bia"},
    ]
    assert sqlite_db.obter_historico_match("bia@email.com", "ana@email.com") == [
        {"remetente": "match", "mensagem": "Oi Bia"},
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


def test_sqlite_user_repository_cria_e_autentica_usuario(tmp_path, monkeypatch):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    repo = sqlite_db.SQLiteUserRepository()

    assert repo.criar_usuario("ana@email.com", "segredo", nome="Ana") is True
    assert repo.criar_usuario("ana@email.com", "segredo", nome="Ana 2") is False

    usuario = repo.buscar_usuario_por_email("ana@email.com")

    assert usuario["nome"] == "Ana"
    assert usuario["senha_hash"] != "segredo"

    controller = LoginController(repo)

    assert controller.realizar_login("ana@email.com", "segredo")["nome"] == "Ana"
    assert controller.realizar_login("ana@email.com", "senha-errada") is None


def test_sqlite_user_repository_cria_usuario_com_perfil_default_incompleto(
    tmp_path,
    monkeypatch,
):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    repo = sqlite_db.SQLiteUserRepository()

    assert repo.criar_usuario("fellipe@example.com", "segredo") is True

    usuario = repo.buscar_usuario_por_email("fellipe@example.com")
    perfil = sqlite_db.obter_perfil_publico("fellipe@example.com")

    assert usuario["nome"] == "Fellipe"
    assert perfil["nome"] == "Fellipe"
    assert perfil["descricao"] == "Perfil em construcao."


def test_migrar_usuario_legado_mescla_matches_sem_apagar_mensagens(
    tmp_path,
    monkeypatch,
):
    banco_teste = tmp_path / "teste.db"
    monkeypatch.setattr(sqlite_db, "DB_PATH", banco_teste)

    sqlite_db.iniciar_banco_sqlite()
    conn = sqlite3.connect(banco_teste)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO historico_chat
        (usuario, remetente, mensagem, data_hora)
        VALUES ('user_rafaell', 'usuario', 'Oi legado', '2026-01-01')
        """
    )
    cursor.execute(
        """
        INSERT INTO vetores_salvos
        (usuario, vetores_json, data_hora)
        VALUES ('user_rafaell', '{"psicologico": {}}', '2026-01-01')
        """
    )
    cursor.execute(
        """
        INSERT INTO logs_api
        (usuario, endpoint, acao, status, mensagem, data_hora)
        VALUES ('user_rafaell', '/chat', 'teste', 'sucesso', 'ok', '2026-01-01')
        """
    )
    cursor.execute(
        """
        INSERT INTO matches_usuario
        (usuario, match_id, nome, afinidade, dados_match_json, data_hora)
        VALUES (?, 'user_maria', 'Maria destino', '90%', NULL, '2026-01-01')
        """,
        (ADMIN_EMAIL,),
    )
    cursor.execute(
        """
        INSERT INTO matches_usuario
        (usuario, match_id, nome, afinidade, dados_match_json, data_hora)
        VALUES ('user_rafaell', 'user_maria', 'Maria legado', '85%', NULL, '2026-01-01')
        """
    )
    cursor.execute(
        """
        INSERT INTO matches_usuario
        (usuario, match_id, nome, afinidade, dados_match_json, data_hora)
        VALUES ('user_rafaell', 'user_carmen', 'Carmen legado', '80%', NULL, '2026-01-01')
        """
    )
    cursor.execute(
        """
        INSERT INTO mensagens_match
        (usuario, match_id, remetente, mensagem, data_hora)
        VALUES ('user_rafaell', 'user_maria', 'usuario', 'Oi Maria legado', '2026-01-01')
        """
    )
    cursor.execute(
        """
        INSERT INTO mensagens_match
        (usuario, match_id, remetente, mensagem, data_hora)
        VALUES ('user_rafaell', 'user_carmen', 'usuario', 'Oi Carmen legado', '2026-01-01')
        """
    )
    conn.commit()
    conn.close()

    sqlite_db.migrar_usuario_legado_sqlite()
    sqlite_db.migrar_usuario_legado_sqlite()

    conn = sqlite3.connect(banco_teste)
    usuarios_legados = list(
        conn.execute(
            """
            SELECT usuario FROM historico_chat WHERE usuario = 'user_rafaell'
            UNION ALL
            SELECT usuario FROM matches_usuario WHERE usuario = 'user_rafaell'
            UNION ALL
            SELECT usuario FROM mensagens_match WHERE usuario = 'user_rafaell'
            UNION ALL
            SELECT usuario FROM vetores_salvos WHERE usuario = 'user_rafaell'
            UNION ALL
            SELECT usuario FROM logs_api WHERE usuario = 'user_rafaell'
            """
        )
    )
    matches_admin = list(
        conn.execute(
            """
            SELECT match_id, nome
            FROM matches_usuario
            WHERE usuario = ?
            ORDER BY match_id
            """,
            (ADMIN_EMAIL,),
        )
    )
    mensagens_admin = list(
        conn.execute(
            """
            SELECT match_id, mensagem
            FROM mensagens_match
            WHERE usuario = ?
            ORDER BY match_id, id
            """,
            (ADMIN_EMAIL,),
        )
    )
    historico_admin = list(
        conn.execute(
            "SELECT mensagem FROM historico_chat WHERE usuario = ?",
            (ADMIN_EMAIL,),
        )
    )
    conn.close()

    assert usuarios_legados == []
    assert matches_admin == [
        ("user_carmen", "Carmen legado"),
        ("user_maria", "Maria destino"),
    ]
    assert mensagens_admin == [
        ("user_carmen", "Oi Carmen legado"),
        ("user_maria", "Oi Maria legado"),
    ]
    assert historico_admin == [("Oi legado",)]

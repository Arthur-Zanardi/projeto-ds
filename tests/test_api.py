from fastapi.testclient import TestClient

from src.controllers import api
from src.services import sqlite_db


ADMIN_EMAIL = "rafaellapipucos@gmail.com"
HEADERS_ADMIN = {
    "X-Usuario-Email": ADMIN_EMAIL,
    "X-Usuario-Nome": "Rafaell",
}
HEADERS_FELLIPE = {
    "X-Usuario-Email": "fellipe@example.com",
    "X-Usuario-Nome": "Fellipe",
}
HEADERS_FERNANDO = {
    "X-Usuario-Email": "fernando@example.com",
    "X-Usuario-Nome": "Fernando",
}


def desativar_logs(monkeypatch):
    monkeypatch.setattr(api, "registrar_evento", lambda **kwargs: None)


def test_chat_salva_mensagem_do_usuario_e_resposta_da_ia(monkeypatch):
    desativar_logs(monkeypatch)
    mensagens_salvas = []
    chamadas = {
        "texto_extraido": None,
        "vetores_salvos": None,
        "perfil_salvo": None,
    }
    vetores = {
        "psicologico": {"extroversao": 0.64},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 0.96},
    }

    def salvar_mensagem_fake(**kwargs):
        mensagens_salvas.append(kwargs)

    def extrair_vetores_fake(texto):
        chamadas["texto_extraido"] = texto
        return vetores

    def salvar_vetores_fake(**kwargs):
        chamadas["vetores_salvos"] = kwargs

    def salvar_perfil_fake(id_usuario, nome, dados_extraidos_ia):
        chamadas["perfil_salvo"] = (id_usuario, nome, dados_extraidos_ia)
        return [0.64, 0.2, 0.96]

    monkeypatch.setattr(api, "salvar_mensagem", salvar_mensagem_fake)
    monkeypatch.setattr(api, "gerar_resposta_ia", lambda texto: "Resposta da IA")
    monkeypatch.setattr(
        api,
        "obter_historico_chat",
        lambda usuario: [{"remetente": "usuario", "mensagem": "Oi"}],
    )
    monkeypatch.setattr(api, "extrair_vetores_da_conversa", extrair_vetores_fake)
    monkeypatch.setattr(api, "salvar_vetores_sqlite", salvar_vetores_fake)
    monkeypatch.setattr(api, "salvar_perfil_usuario", salvar_perfil_fake)

    resposta = api.conversar_com_ia(api.MensagemTextoObrigatorio(texto="Oi"))

    assert resposta == {"resposta": "Resposta da IA", "perfil_atualizado": True}
    assert mensagens_salvas == [
            {
                "usuario": ADMIN_EMAIL,
                "remetente": "usuario",
                "mensagem": "Oi",
            },
            {
                "usuario": ADMIN_EMAIL,
                "remetente": "ia",
                "mensagem": "Resposta da IA",
            },
        ]
    assert chamadas["texto_extraido"] == "Oi"
    assert chamadas["vetores_salvos"] == {
        "usuario": ADMIN_EMAIL,
        "vetores_dict": vetores,
    }
    assert chamadas["perfil_salvo"] == (ADMIN_EMAIL, "Rafaell", vetores)


def test_historico_retorna_mensagens_salvas(monkeypatch):
    desativar_logs(monkeypatch)
    historico = [{"remetente": "usuario", "mensagem": "Oi"}]
    monkeypatch.setattr(
        api,
        "obter_historico_chat",
        lambda usuario: historico,
    )

    resposta = api.pegar_historico()

    assert resposta == {"historico": historico}


def test_matches_criam_listam_e_mantem_mensagens_separadas(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    client = TestClient(api.app)

    resposta_maria = client.post(
        "/matches",
        json={
            "id": "user_maria",
            "nome": "Maria",
            "afinidade": "85%",
            "idade": 27,
        },
    )
    resposta_joao = client.post(
        "/matches",
        json={"match_id": "user_joao", "nome": "Joao"},
    )

    assert resposta_maria.status_code == 201
    assert resposta_joao.status_code == 201
    assert resposta_maria.json()["match"]["match_id"] == "user_maria"
    assert resposta_maria.json()["match"]["dados_match"]["idade"] == 27

    resposta_listar = client.get("/matches")

    assert resposta_listar.status_code == 200
    assert [
        match["match_id"]
        for match in resposta_listar.json()["matches"]
    ] == ["user_maria", "user_joao"]

    resposta_msg_maria = client.post(
        "/matches/user_maria/mensagens",
        json={"texto": "Oi, Maria"},
    )
    client.post(
        "/matches/user_joao/mensagens",
        json={"mensagem": "Oi, Joao"},
    )
    client.post(
        "/matches/user_maria/mensagens",
        json={"texto": "Tudo bem?", "remetente": "match"},
    )

    assert resposta_msg_maria.status_code == 201
    assert resposta_msg_maria.json()["mensagem"] == {
        "match_id": "user_maria",
        "remetente": "usuario",
        "mensagem": "Oi, Maria",
    }

    resposta_historico_maria = client.get("/matches/user_maria/mensagens")

    assert resposta_historico_maria.status_code == 200
    assert resposta_historico_maria.json() == {
        "match_id": "user_maria",
        "mensagens": [
            {"remetente": "usuario", "mensagem": "Oi, Maria"},
            {"remetente": "match", "mensagem": "Tudo bem?"},
        ],
    }


def test_historico_matches_e_mensagens_sao_separados_por_email(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    vetores = {
        "psicologico": {"extroversao": 0.64},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 0.96},
    }

    monkeypatch.setattr(api, "gerar_resposta_ia", lambda texto: f"IA: {texto}")
    monkeypatch.setattr(api, "extrair_vetores_da_conversa", lambda texto: vetores)
    monkeypatch.setattr(api, "salvar_perfil_usuario", lambda *args: [0.64, 0.2, 0.96])
    client = TestClient(api.app)

    client.post("/chat", headers=HEADERS_FELLIPE, json={"texto": "Oi Fellipe"})
    client.post("/chat", headers=HEADERS_FERNANDO, json={"texto": "Oi Fernando"})

    historico_fellipe = client.get(
        "/historico",
        headers=HEADERS_FELLIPE,
    ).json()["historico"]
    historico_fernando = client.get(
        "/historico",
        headers=HEADERS_FERNANDO,
    ).json()["historico"]

    assert historico_fellipe == [
        {"remetente": "usuario", "mensagem": "Oi Fellipe"},
        {"remetente": "ia", "mensagem": "IA: Oi Fellipe"},
    ]
    assert historico_fernando == [
        {"remetente": "usuario", "mensagem": "Oi Fernando"},
        {"remetente": "ia", "mensagem": "IA: Oi Fernando"},
    ]

    client.post(
        "/matches",
        headers=HEADERS_FELLIPE,
        json={"id": "user_maria", "nome": "Maria"},
    )
    client.post(
        "/matches",
        headers=HEADERS_FERNANDO,
        json={"id": "user_joao", "nome": "Joao"},
    )
    client.post(
        "/matches/user_maria/mensagens",
        headers=HEADERS_FELLIPE,
        json={"mensagem": "Oi, Maria"},
    )
    client.post(
        "/matches/user_joao/mensagens",
        headers=HEADERS_FERNANDO,
        json={"mensagem": "Oi, Joao"},
    )

    matches_fellipe = client.get(
        "/matches",
        headers=HEADERS_FELLIPE,
    ).json()["matches"]
    matches_fernando = client.get(
        "/matches",
        headers=HEADERS_FERNANDO,
    ).json()["matches"]

    assert [match["match_id"] for match in matches_fellipe] == ["user_maria"]
    assert [match["match_id"] for match in matches_fernando] == ["user_joao"]
    assert client.get(
        "/matches/user_maria/mensagens",
        headers=HEADERS_FELLIPE,
    ).json()["mensagens"] == [
        {"remetente": "usuario", "mensagem": "Oi, Maria"},
    ]
    assert client.get(
        "/matches/user_joao/mensagens",
        headers=HEADERS_FERNANDO,
    ).json()["mensagens"] == [
        {"remetente": "usuario", "mensagem": "Oi, Joao"},
    ]


def test_criar_mock_customizado_exige_admin(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    client = TestClient(api.app)
    payload = {
        "id": "custom_luna",
        "nome": "Luna",
        "dados_match": {"mock_customizado": True},
    }

    resposta_comum = client.post(
        "/matches",
        headers=HEADERS_FELLIPE,
        json=payload,
    )
    resposta_admin = client.post(
        "/matches",
        headers=HEADERS_ADMIN,
        json=payload,
    )

    assert resposta_comum.status_code == 403
    assert resposta_comum.json() == {
        "detail": "Apenas administradores podem criar perfis mock."
    }
    assert resposta_admin.status_code == 201
    assert resposta_admin.json()["match"]["usuario"] == ADMIN_EMAIL
    assert resposta_admin.json()["match"]["match_id"] == "custom_luna"


def test_mensagens_de_match_inexistente_retornam_404(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    client = TestClient(api.app)

    resposta_get = client.get("/matches/match_inexistente/mensagens")
    resposta_post = client.post(
        "/matches/match_inexistente/mensagens",
        json={"texto": "Oi"},
    )

    assert resposta_get.status_code == 404
    assert resposta_post.status_code == 404
    assert resposta_get.json() == {"detail": "Match nao encontrado."}
    assert resposta_post.json() == {"detail": "Match nao encontrado."}


def test_chat_sem_texto_retorna_erro_422(monkeypatch):
    desativar_logs(monkeypatch)
    client = TestClient(api.app)

    resposta_sem_campo = client.post("/chat", json={})
    resposta_vazia = client.post("/chat", json={"texto": "   "})

    assert resposta_sem_campo.status_code == 422
    assert resposta_vazia.status_code == 422


def test_analisar_perfil_sem_texto_retorna_erro_422(monkeypatch):
    desativar_logs(monkeypatch)
    client = TestClient(api.app)

    resposta = client.post("/analisar_perfil", json={"texto": ""})

    assert resposta.status_code == 422


def test_chat_com_falha_da_ia_retorna_503(monkeypatch):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(api, "salvar_mensagem", lambda **kwargs: None)

    def gerar_resposta_fake(texto):
        raise api.LLMServiceError("Groq fora do ar")

    monkeypatch.setattr(api, "gerar_resposta_ia", gerar_resposta_fake)
    client = TestClient(api.app)

    resposta = client.post("/chat", json={"texto": "Oi"})

    assert resposta.status_code == 503
    assert resposta.json() == {
        "detail": "Nao foi possivel gerar resposta da IA."
    }


def test_chat_com_falha_ao_atualizar_vetor_retorna_503(monkeypatch):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(api, "salvar_mensagem", lambda **kwargs: None)
    monkeypatch.setattr(api, "gerar_resposta_ia", lambda texto: "Resposta da IA")
    monkeypatch.setattr(
        api,
        "obter_historico_chat",
        lambda usuario: [{"remetente": "usuario", "mensagem": "Oi"}],
    )

    def extrair_vetores_fake(texto):
        raise api.LLMServiceError("falha vetorial")

    monkeypatch.setattr(api, "extrair_vetores_da_conversa", extrair_vetores_fake)
    client = TestClient(api.app)

    resposta = client.post("/chat", json={"texto": "Oi"})

    assert resposta.status_code == 503
    assert resposta.json() == {
        "detail": "Nao foi possivel atualizar o perfil vetorial."
    }


def test_historico_com_falha_de_banco_retorna_503(monkeypatch):
    desativar_logs(monkeypatch)

    def obter_historico_fake(usuario):
        raise RuntimeError("SQLite indisponivel")

    monkeypatch.setattr(api, "obter_historico_chat", obter_historico_fake)
    client = TestClient(api.app)

    resposta = client.get("/historico")

    assert resposta.status_code == 503
    assert resposta.json() == {
        "detail": "Nao foi possivel carregar o historico."
    }


def test_dar_match_retorna_erro_sem_texto_e_sem_historico(monkeypatch):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(api, "obter_ultimo_vetor_sqlite", lambda usuario: None)

    resposta = api.calcular_match_final(api.MensagemMatch(texto="   "))

    assert resposta == {
        "sucesso": False,
        "mensagem": "Ainda nao ha perfil vetorial salvo para calcular um match.",
    }


def test_dar_match_usa_ultimo_vetor_salvo_e_retorna_match(monkeypatch):
    desativar_logs(monkeypatch)
    chamadas = {
        "buscar_match": None,
    }
    vetores = {
        "psicologico": {"extroversao": 0.64},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 0.96},
    }
    match = {
        "id": "user_maria",
        "nome": "Maria",
        "afinidade": "85.3%",
        "distancia_matematica": 0.1467,
        "dimensoes_comparadas": 3,
    }

    def extrair_vetores_fake(texto):
        raise AssertionError("/dar_match nao deve chamar a IA")

    def buscar_match_fake(id_usuario, vetor, quantidade):
        chamadas["buscar_match"] = (id_usuario, vetor, quantidade)
        return [match]

    monkeypatch.setattr(api, "obter_ultimo_vetor_sqlite", lambda usuario: vetores)
    monkeypatch.setattr(api, "extrair_vetores_da_conversa", extrair_vetores_fake)
    monkeypatch.setattr(
        api,
        "buscar_melhor_match",
        buscar_match_fake,
    )

    resposta = api.calcular_match_final(api.MensagemMatch(texto=""))

    assert chamadas["buscar_match"] == (ADMIN_EMAIL, [0.64, 0.2, 0.96], 1)
    assert resposta == {"sucesso": True, "match": match}

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


def test_like_real_exige_reciprocidade_e_compartilha_conversa(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    monkeypatch.setattr(
        api,
        "gerar_sugestoes_para_match",
        lambda usuario, candidato, vetor: [
            {"campo": "musica", "rotulo": "Musica", "texto": "Qual musica descreve sua semana?"}
        ],
    )
    sqlite_db.salvar_perfil_publico(
        usuario="fellipe@example.com",
        nome="Fellipe",
        idade=25,
        descricao="Perfil do Fellipe",
        localizacao="Recife",
        cargo="Dev",
    )
    sqlite_db.salvar_perfil_publico(
        usuario="fernando@example.com",
        nome="Fernando",
        idade=26,
        descricao="Perfil do Fernando",
        localizacao="Olinda",
        cargo="Designer",
    )
    client = TestClient(api.app)

    pendente = client.post(
        "/matches/fernando@example.com/acao",
        headers=HEADERS_FELLIPE,
        json={"acao": "like"},
    )

    assert pendente.status_code == 200
    assert pendente.json()["status"] == "pendente"
    assert client.get("/matches", headers=HEADERS_FELLIPE).json()["matches"] == []

    confirmado = client.post(
        "/matches/fellipe@example.com/acao",
        headers=HEADERS_FERNANDO,
        json={"acao": "like"},
    )

    assert confirmado.status_code == 200
    assert confirmado.json()["status"] == "confirmado"
    assert confirmado.json()["sugestoes"][0]["campo"] == "musica"
    assert [
        match["match_id"]
        for match in client.get("/matches", headers=HEADERS_FELLIPE).json()["matches"]
    ] == ["fernando@example.com"]
    assert [
        match["match_id"]
        for match in client.get("/matches", headers=HEADERS_FERNANDO).json()["matches"]
    ] == ["fellipe@example.com"]

    client.post(
        "/matches/fellipe@example.com/mensagens",
        headers=HEADERS_FERNANDO,
        json={"mensagem": "Oi, Fellipe"},
    )

    assert client.get(
        "/matches/fernando@example.com/mensagens",
        headers=HEADERS_FELLIPE,
    ).json()["mensagens"] == [
        {"remetente": "match", "mensagem": "Oi, Fellipe"},
    ]


def test_like_em_mock_confirma_imediatamente(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    monkeypatch.setattr(api, "gerar_sugestoes_para_match", lambda *args: [])
    sqlite_db.salvar_perfil_publico(
        usuario="user_luna",
        nome="Luna",
        idade=23,
        descricao="Perfil mock",
        localizacao="Recife",
        cargo="Musica",
        origem="mock",
    )
    client = TestClient(api.app)

    resposta = client.post(
        "/matches/user_luna/acao",
        headers=HEADERS_FELLIPE,
        json={"acao": "like"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "confirmado"
    assert [
        match["match_id"]
        for match in client.get("/matches", headers=HEADERS_FELLIPE).json()["matches"]
    ] == ["user_luna"]


def test_acao_match_funciona_sem_perfil_publico_previo(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    monkeypatch.setattr(api, "gerar_sugestoes_para_match", lambda *args: [])
    client = TestClient(api.app)

    recusa = client.post(
        "/matches/user_sem_perfil/acao",
        headers=HEADERS_FELLIPE,
        json={"acao": "pass"},
    )
    like_mock = client.post(
        "/matches/user_sem_perfil/acao",
        headers=HEADERS_FELLIPE,
        json={"acao": "like"},
    )

    assert recusa.status_code == 200
    assert recusa.json()["status"] == "recusado"
    assert like_mock.status_code == 200
    assert like_mock.json()["status"] == "confirmado"
    assert like_mock.json()["match"]["nome"] == "Sem Perfil"


def test_atualizar_perfil_publico_aceita_idade_textual(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    client = TestClient(api.app)

    resposta = client.put(
        "/perfil_publico",
        headers=HEADERS_FELLIPE,
        json={
            "nome": "Fellipe",
            "idade": "vinte e cinco",
            "descricao": "Bio",
            "localizacao": "Recife",
            "cargo": "Dev",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["perfil"]["idade"] is None


def test_atualizar_perfil_publico_salva_foto_e_status_completo(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    client = TestClient(api.app)

    resposta = client.put(
        "/perfil_publico",
        headers=HEADERS_FELLIPE,
        json={
            "nome": "Fellipe",
            "idade": "25",
            "foto_url": "uploads/profile_images/fellipe/foto.jpg",
            "descricao": "Bio completa",
            "localizacao": "Recife",
            "cargo": "Dev",
        },
    )

    perfil = resposta.json()["perfil"]

    assert resposta.status_code == 200
    assert perfil["foto_url"] == "uploads/profile_images/fellipe/foto.jpg"
    assert perfil["perfil_completo"] is True
    assert perfil["campos_faltantes"] == []


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


def test_endpoint_perfis_mock_exige_admin_e_salva_vetor(
    tmp_path,
    monkeypatch,
):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(sqlite_db, "DB_PATH", tmp_path / "teste.db")
    chamadas = {}
    monkeypatch.setattr(
        api,
        "salvar_perfil_vetorial",
        lambda perfil_id, nome, vetores: chamadas.setdefault(
            "vetor",
            (perfil_id, nome, vetores),
        ),
    )
    client = TestClient(api.app)
    payload = {
        "id": "custom_luna",
        "nome": "Luna",
        "idade": 22,
        "descricao": "Perfil mock",
        "localizacao": "Recife",
        "cargo": "Musica",
        "vetores": {"psicologico": {"extroversao": 0.8}},
    }

    resposta_comum = client.post(
        "/perfis_mock",
        headers=HEADERS_FELLIPE,
        json=payload,
    )
    resposta_admin = client.post(
        "/perfis_mock",
        headers=HEADERS_ADMIN,
        json=payload,
    )

    assert resposta_comum.status_code == 403
    assert resposta_admin.status_code == 201
    assert resposta_admin.json()["perfil"]["usuario"] == "custom_luna"
    assert resposta_admin.json()["perfil"]["mock_customizado"] is True
    assert chamadas["vetor"] == (
        "custom_luna",
        "Luna",
        {"psicologico": {"extroversao": 0.8}},
    )


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
    monkeypatch.setattr(
        api,
        "perfil_publico_ou_padrao",
        lambda usuario: {
            "nome": "Rafaell",
            "idade": 25,
            "foto_url": "uploads/profile_images/rafaell/foto.jpg",
            "descricao": "Bio completa",
            "localizacao": "Recife",
            "cargo": "Dev",
        },
    )
    monkeypatch.setattr(api, "obter_ultimo_vetor_sqlite", lambda usuario: None)

    resposta = api.calcular_match_final(api.MensagemMatch(texto="   "))

    assert resposta == {
        "sucesso": False,
        "mensagem": "Ainda nao ha perfil vetorial salvo para calcular um match.",
    }


def test_dar_match_bloqueia_perfil_publico_incompleto(monkeypatch):
    desativar_logs(monkeypatch)
    monkeypatch.setattr(
        api,
        "perfil_publico_ou_padrao",
        lambda usuario: {
            "nome": "Fellipe",
            "idade": 25,
            "foto_url": "",
            "descricao": "Bio",
            "localizacao": "Recife",
            "cargo": "Dev",
        },
    )
    monkeypatch.setattr(
        api,
        "obter_ultimo_vetor_sqlite",
        lambda usuario: {"psicologico": {"extroversao": 0.5}},
    )

    resposta = api.calcular_match_final(api.MensagemMatch(texto=""))

    assert resposta == {
        "sucesso": False,
        "perfil_incompleto": True,
        "campos_faltantes": ["foto_url"],
        "mensagem": "Complete seu perfil antes de descobrir matches.",
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
    perfil_maria = {
        "id": "user_maria",
        "match_id": "user_maria",
        "usuario": "user_maria",
        "nome": "Maria",
        "idade": 22,
        "imagem": "foto.jpg",
        "foto_url": "foto.jpg",
        "descricao": "Perfil de Maria",
        "localizacao": "Recife",
        "cargo": "Designer",
        "origem": "mock",
        "tipo": "mock",
        "mock_customizado": False,
        "data_hora": "2026-01-01",
    }

    def extrair_vetores_fake(texto):
        raise AssertionError("/dar_match nao deve chamar a IA")

    def buscar_match_fake(
        id_usuario,
        vetor,
        quantidade,
        ids_ignorados=None,
        incluir_vetor=False,
    ):
        chamadas["buscar_match"] = (
            id_usuario,
            vetor,
            quantidade,
            ids_ignorados,
            incluir_vetor,
        )
        return [match]

    monkeypatch.setattr(api, "obter_ultimo_vetor_sqlite", lambda usuario: vetores)
    monkeypatch.setattr(api, "extrair_vetores_da_conversa", extrair_vetores_fake)
    monkeypatch.setattr(
        api,
        "perfil_publico_ou_padrao",
        lambda usuario: {
            "nome": "Rafaell",
            "idade": 25,
            "foto_url": "uploads/profile_images/rafaell/foto.jpg",
            "descricao": "Bio completa",
            "localizacao": "Recife",
            "cargo": "Dev",
        },
    )
    monkeypatch.setattr(api, "listar_ids_indisponiveis_match", lambda usuario: {"user_carmen"})
    monkeypatch.setattr(api, "obter_perfil_publico", lambda usuario: perfil_maria)
    monkeypatch.setattr(
        api,
        "buscar_melhor_match",
        buscar_match_fake,
    )

    resposta = api.calcular_match_final(api.MensagemMatch(texto=""))

    vetor_usado = chamadas["buscar_match"][1]
    assert chamadas["buscar_match"] == (
        ADMIN_EMAIL,
        vetor_usado,
        20,
        {"user_carmen"},
        True,
    )
    assert len(vetor_usado) == len(api.achatar_dados_vetoriais(vetores))
    assert resposta == {
        "sucesso": True,
        "match": perfil_maria,
        "matches": [perfil_maria],
    }
    assert "afinidade" not in resposta["match"]

from fastapi.testclient import TestClient

from src.controllers import api


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
            "usuario": "user_rafaell",
            "remetente": "usuario",
            "mensagem": "Oi",
        },
        {
            "usuario": "user_rafaell",
            "remetente": "ia",
            "mensagem": "Resposta da IA",
        },
    ]
    assert chamadas["texto_extraido"] == "Oi"
    assert chamadas["vetores_salvos"] == {
        "usuario": "user_rafaell",
        "vetores_dict": vetores,
    }
    assert chamadas["perfil_salvo"] == ("user_rafaell", "Rafaell", vetores)


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

    assert chamadas["buscar_match"] == ("user_rafaell", [0.64, 0.2, 0.96], 1)
    assert resposta == {"sucesso": True, "match": match}

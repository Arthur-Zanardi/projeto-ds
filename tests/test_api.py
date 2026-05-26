from src.controllers import api


def test_chat_salva_mensagem_do_usuario_e_resposta_da_ia(monkeypatch):
    mensagens_salvas = []

    def salvar_mensagem_fake(**kwargs):
        mensagens_salvas.append(kwargs)

    monkeypatch.setattr(api, "salvar_mensagem", salvar_mensagem_fake)
    monkeypatch.setattr(api, "gerar_resposta_ia", lambda texto: "Resposta da IA")

    resposta = api.conversar_com_ia(api.MensagemUsuario(texto="Oi"))

    assert resposta == {"resposta": "Resposta da IA"}
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


def test_historico_retorna_mensagens_salvas(monkeypatch):
    historico = [{"remetente": "usuario", "mensagem": "Oi"}]
    monkeypatch.setattr(
        api,
        "obter_historico_chat",
        lambda usuario: historico,
    )

    resposta = api.pegar_historico()

    assert resposta == {"historico": historico}


def test_dar_match_retorna_erro_sem_texto_e_sem_historico(monkeypatch):
    monkeypatch.setattr(api, "obter_historico_chat", lambda usuario: [])

    resposta = api.calcular_match_final(api.MensagemUsuario(texto="   "))

    assert resposta == {
        "sucesso": False,
        "mensagem": "Ainda nao ha conversa suficiente para calcular um match.",
    }


def test_dar_match_usa_historico_e_retorna_match(monkeypatch):
    chamadas = {
        "texto_extraido": None,
        "vetores_salvos": None,
        "perfil_salvo": None,
    }
    historico = [
        {"remetente": "usuario", "mensagem": "Gosto de musica"},
        {"remetente": "ia", "mensagem": "Legal"},
        {"remetente": "usuario", "mensagem": "Tambem gosto de tecnologia"},
    ]
    vetores = {
        "psicologico": {"extroversao": 0.5},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 1.0},
    }
    match = {
        "id": "user_maria",
        "nome": "Maria",
        "afinidade": "82.0%",
        "distancia_matematica": 0.18,
    }

    def extrair_vetores_fake(texto):
        chamadas["texto_extraido"] = texto
        return vetores

    def salvar_vetores_fake(**kwargs):
        chamadas["vetores_salvos"] = kwargs

    def salvar_perfil_fake(id_usuario, nome, dados_extraidos_ia):
        chamadas["perfil_salvo"] = (id_usuario, nome, dados_extraidos_ia)
        return [0.5, 0.2, 1.0]

    monkeypatch.setattr(api, "obter_historico_chat", lambda usuario: historico)
    monkeypatch.setattr(api, "extrair_vetores_da_conversa", extrair_vetores_fake)
    monkeypatch.setattr(api, "salvar_vetores_sqlite", salvar_vetores_fake)
    monkeypatch.setattr(api, "salvar_perfil_usuario", salvar_perfil_fake)
    monkeypatch.setattr(
        api,
        "buscar_melhor_match",
        lambda id_usuario, vetor, quantidade: [match],
    )

    resposta = api.calcular_match_final(api.MensagemUsuario(texto=""))

    assert chamadas["texto_extraido"] == (
        "Gosto de musica\nTambem gosto de tecnologia"
    )
    assert chamadas["vetores_salvos"] == {
        "usuario": "user_rafaell",
        "vetores_dict": vetores,
    }
    assert chamadas["perfil_salvo"] == ("user_rafaell", "Rafaell", vetores)
    assert resposta == {"sucesso": True, "match": match}

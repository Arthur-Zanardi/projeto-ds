"""Testes de integração da API com autenticação JWT e PostgreSQL."""
import pytest

from src.controllers import api


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setattr(api, "gerar_resposta_ia", lambda *a, **k: "Resposta da IA")
    monkeypatch.setattr(
        api,
        "extrair_vetores_da_conversa",
        lambda *a, **k: {
            "psicologico": {"extroversao": 0.8, "ritmo_vida": 0.7, "romantismo_afeto": 0.6},
            "valores": {},
            "interesses": {"musica": 0.9},
        },
    )


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["database"] == "conectado"


def test_chat_salva_mensagem_e_responde(client, auth, mock_llm):
    headers = auth("user@example.com", nome="User")
    resp = client.post("/chat", headers=headers, json={"texto": "Oi, gosto de musica"})
    assert resp.status_code == 200
    assert resp.json()["resposta"] == "Resposta da IA"

    historico = client.get("/historico", headers=headers).json()["historico"]
    assert any(m["remetente"] == "usuario" for m in historico)
    assert any(m["remetente"] == "ia" for m in historico)


def test_chat_isola_historico_por_usuario(client, auth, mock_llm):
    h1 = auth("a@example.com")
    h2 = auth("b@example.com")
    client.post("/chat", headers=h1, json={"texto": "sou o A"})
    client.post("/chat", headers=h2, json={"texto": "sou o B"})
    hist1 = client.get("/historico", headers=h1).json()["historico"]
    textos1 = [m["mensagem"] for m in hist1]
    assert "sou o A" in textos1
    assert "sou o B" not in textos1


def test_perfil_publico_get_e_update(client, auth):
    headers = auth("p@example.com", nome="Pedro")
    assert client.get("/perfil_publico", headers=headers).status_code == 200
    resp = client.put(
        "/perfil_publico",
        headers=headers,
        json={
            "nome": "Pedro",
            "idade": 25,
            "descricao": "Bio do Pedro",
            "localizacao": "Recife",
            "cargo": "Dev",
            "foto_url": "http://img/x.png",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["perfil"]["idade"] == 25


def test_criar_listar_match_e_pass(client, auth):
    headers = auth("m@example.com")
    resp = client.post("/matches", headers=headers, json={"id": "user_maria", "nome": "Maria"})
    assert resp.status_code == 201
    matches = client.get("/matches", headers=headers).json()["matches"]
    assert len(matches) == 1
    resp = client.post("/matches/user_maria/acao", headers=headers, json={"acao": "pass"})
    assert resp.status_code == 200
    assert resp.json()["match_confirmado"] is False


def test_like_em_mock_confirma_e_permite_mensagem(client, auth):
    headers = auth("k@example.com")
    resp = client.post("/matches/user_maria/acao", headers=headers, json={"acao": "like"})
    assert resp.status_code == 200
    assert resp.json()["match_confirmado"] is True
    resp = client.post(
        "/matches/user_maria/mensagens", headers=headers, json={"mensagem": "Oi Maria"}
    )
    assert resp.status_code == 201

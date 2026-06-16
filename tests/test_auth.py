"""Testes de autenticação JWT: registro, login, 401 e 403."""


def test_registro_retorna_token(client):
    resp = client.post(
        "/auth/register", json={"email": "ana@example.com", "senha": "senha123", "nome": "Ana"}
    )
    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["access_token"]
    assert corpo["usuario"]["email"] == "ana@example.com"


def test_login_com_senha_errada_retorna_401(client):
    client.post("/auth/register", json={"email": "bia@example.com", "senha": "certa123"})
    resp = client.post("/auth/login", json={"email": "bia@example.com", "senha": "errada"})
    assert resp.status_code == 401


def test_endpoint_protegido_sem_token_retorna_401(client):
    assert client.get("/matches").status_code == 401
    assert client.get("/perfil_publico").status_code == 401


def test_endpoint_protegido_com_token_funciona(client, auth):
    headers = auth("carla@example.com")
    resp = client.get("/matches", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"matches": []}


def test_admin_endpoint_bloqueia_nao_admin_403(client, auth):
    headers = auth("naoadmin@example.com")
    resp = client.post(
        "/perfis_mock", headers=headers, json={"nome": "Mock", "id": "custom_x"}
    )
    assert resp.status_code == 403


def test_admin_endpoint_permite_admin(client, auth):
    # admin@example.com está em ADMIN_EMAILS (conftest)
    headers = auth("admin@example.com")
    resp = client.post(
        "/perfis_mock", headers=headers, json={"nome": "Mock Admin", "id": "custom_admin"}
    )
    assert resp.status_code == 201
    assert resp.json()["perfil"]["nome"] == "Mock Admin"

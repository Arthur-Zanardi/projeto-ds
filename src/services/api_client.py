import asyncio
import logging
import os

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("MATCHAI_API_BASE_URL", "http://127.0.0.1:8000")


def montar_headers_usuario(usuario_logado: dict | None = None):
    if not isinstance(usuario_logado, dict):
        return {}

    email = str(usuario_logado.get("email") or "").strip().lower()
    nome = str(usuario_logado.get("nome") or "").strip()
    headers = {}

    if email:
        headers["X-Usuario-Email"] = email

    if nome:
        headers["X-Usuario-Nome"] = nome

    return headers


def _json_ou_vazio(resposta):
    try:
        return resposta.json()
    except ValueError:
        return {}


async def enviar_mensagem_chat(texto: str, usuario_logado: dict | None = None) -> str:
    try:
        resposta_api = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/chat",
            timeout=15,
            json={"texto": texto},
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta_api.status_code == 200:
            return resposta_api.json().get(
                "resposta",
                "Desculpe, nao consegui obter uma resposta da IA.",
            )

        return f"Erro na API: {resposta_api.status_code}"

    except Exception as ex:
        return f"Erro de conexao com o servidor local: {ex}. A API esta rodando?"


async def carregar_historico(usuario_logado: dict | None = None):
    try:
        resposta = await asyncio.to_thread(
            requests.get,
            f"{API_BASE_URL}/historico",
            timeout=5,
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code == 200:
            return resposta.json().get("historico", [])

        return []

    except Exception as e:
        logger.warning("Nao foi possivel carregar historico. API desligada? Erro: %s", e)
        return []


async def carregar_perfil_publico(usuario_logado: dict | None = None):
    try:
        resposta = await asyncio.to_thread(
            requests.get,
            f"{API_BASE_URL}/perfil_publico",
            timeout=5,
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code == 200:
            return resposta.json().get("perfil")

        return None
    except Exception as erro:
        logger.warning("Nao foi possivel carregar perfil publico. Erro: %s", erro)
        return None


async def salvar_perfil_publico(perfil: dict, usuario_logado: dict | None = None):
    try:
        resposta = await asyncio.to_thread(
            requests.put,
            f"{API_BASE_URL}/perfil_publico",
            timeout=8,
            json=perfil,
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code == 200:
            return {"sucesso": True, "perfil": resposta.json().get("perfil")}

        return {"sucesso": False, "mensagem": f"Erro ao salvar perfil: {resposta.status_code}"}
    except Exception as erro:
        return {"sucesso": False, "mensagem": f"Erro ao salvar perfil: {erro}"}


async def dar_match(historico_mensagens: list[str], usuario_logado: dict | None = None):
    try:
        historico_completo = "\n".join(historico_mensagens)
        resposta = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/dar_match",
            timeout=45,
            json={"texto": historico_completo},
            headers=montar_headers_usuario(usuario_logado),
        )
        dados = _json_ou_vazio(resposta)

        if resposta.status_code == 200 and dados.get("sucesso"):
            return {
                "sucesso": True,
                "match": dados["match"],
                "matches": dados.get("matches", [dados["match"]]),
            }

        return {
            "sucesso": False,
            "perfil_incompleto": bool(dados.get("perfil_incompleto")),
            "campos_faltantes": dados.get("campos_faltantes", []),
            "mensagem": dados.get("mensagem", "Nao foi possivel encontrar um match."),
        }

    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro na requisicao: {erro}. A API esta ligada?",
        }


async def registrar_acao_match(
    match_id: str,
    acao: str,
    usuario_logado: dict | None = None,
):
    try:
        resposta = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/matches/{match_id}/acao",
            timeout=8,
            json={"acao": acao},
            headers=montar_headers_usuario(usuario_logado),
        )
        dados = _json_ou_vazio(resposta)

        if resposta.status_code == 200:
            return {"sucesso": True, **dados}

        return {
            "sucesso": False,
            "mensagem": dados.get("detail", f"Erro ao registrar acao: {resposta.status_code}"),
        }
    except Exception as erro:
        return {"sucesso": False, "mensagem": f"Erro ao registrar acao: {erro}"}


async def listar_matches(usuario_logado: dict | None = None):
    try:
        resposta = await asyncio.to_thread(
            requests.get,
            f"{API_BASE_URL}/matches",
            timeout=5,
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code == 200:
            return resposta.json().get("matches", [])

        return []
    except Exception as erro:
        logger.warning("Nao foi possivel carregar matches. Erro: %s", erro)
        return []


async def criar_match(match: dict, usuario_logado: dict | None = None):
    match_id = str(match.get("match_id") or match.get("id") or "").strip()
    nome = str(match.get("nome") or "Seu Match").strip()

    if not match_id:
        return {"sucesso": False, "mensagem": "Match sem id."}

    payload = {
        "id": match_id,
        "nome": nome,
        "dados_match": {
            **match,
            "id": match_id,
            "match_id": match_id,
            "nome": nome,
        },
    }

    try:
        resposta = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/matches",
            timeout=8,
            json=payload,
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code in (200, 201):
            return {"sucesso": True, "match": resposta.json().get("match")}

        return {
            "sucesso": False,
            "mensagem": f"Erro ao salvar match: {resposta.status_code}",
        }
    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro ao salvar match: {erro}. A API esta ligada?",
        }


async def criar_perfil_mock(perfil: dict, usuario_logado: dict | None = None):
    try:
        resposta = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/perfis_mock",
            timeout=10,
            json=perfil,
            headers=montar_headers_usuario(usuario_logado),
        )
        dados = _json_ou_vazio(resposta)

        if resposta.status_code in (200, 201):
            return {"sucesso": True, "perfil": dados.get("perfil")}

        return {
            "sucesso": False,
            "mensagem": dados.get("detail", f"Erro ao criar mock: {resposta.status_code}"),
        }
    except Exception as erro:
        return {"sucesso": False, "mensagem": f"Erro ao criar mock: {erro}"}


async def carregar_historico_match(match_id: str, usuario_logado: dict | None = None):
    try:
        resposta = await asyncio.to_thread(
            requests.get,
            f"{API_BASE_URL}/matches/{match_id}/mensagens",
            timeout=5,
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code == 200:
            return resposta.json().get("mensagens", [])

        return []
    except Exception as erro:
        logger.warning("Nao foi possivel carregar conversa do match. Erro: %s", erro)
        return []


async def salvar_mensagem_match(
    match_id: str,
    mensagem: str,
    remetente: str = "usuario",
    usuario_logado: dict | None = None,
):
    try:
        resposta = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/matches/{match_id}/mensagens",
            timeout=8,
            json={"mensagem": mensagem, "remetente": remetente},
            headers=montar_headers_usuario(usuario_logado),
        )

        if resposta.status_code in (200, 201):
            return {"sucesso": True, "mensagem": resposta.json().get("mensagem")}

        return {
            "sucesso": False,
            "mensagem": f"Erro ao salvar mensagem: {resposta.status_code}",
        }
    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro ao salvar mensagem: {erro}. A API esta ligada?",
        }

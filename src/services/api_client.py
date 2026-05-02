import requests
import asyncio


API_BASE_URL = "http://127.0.0.1:8000"


async def enviar_mensagem_chat(texto: str) -> str:
    try:
        resposta_api = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/chat",
            timeout=15,
            json={"texto": texto},
        )

        if resposta_api.status_code == 200:
            return resposta_api.json().get(
                "resposta",
                "Desculpe, não consegui obter uma resposta da IA."
            )

        return f"Erro na API: {resposta_api.status_code}"

    except Exception as ex:
        return f"Erro de conexão com o servidor local: {ex}. A API está rodando?"


async def carregar_historico():
    try:
        resposta = await asyncio.to_thread(
            requests.get,
            f"{API_BASE_URL}/historico",
            timeout=5,
        )

        if resposta.status_code == 200:
            return resposta.json().get("historico", [])

        return []

    except Exception as e:
        print(f"Aviso: Não foi possível carregar histórico. API desligada? Erro: {e}")
        return []


async def dar_match(historico_mensagens: list[str]):
    try:
        historico_completo = "\n".join(historico_mensagens)

        resposta = await asyncio.to_thread(
            requests.post,
            f"{API_BASE_URL}/dar_match",
            timeout=45,
            json={"texto": historico_completo},
        )

        dados = resposta.json()

        if dados.get("sucesso"):
            return {
                "sucesso": True,
                "match": dados["match"],
            }

        return {
            "sucesso": False,
            "mensagem": dados.get("mensagem", "Não foi possível encontrar um match."),
        }

    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro na requisição: {erro}. A API está ligada?",
        }
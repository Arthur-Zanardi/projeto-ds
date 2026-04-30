import requests

def llm_conversation(mensagem_usuario):
    try:
        resposta_api = requests.post(
            "http://127.0.0.1:8001/chat",
            timeout=15,
            json={"texto": mensagem_usuario}
        )

        if resposta_api.status_code == 200:
            return resposta_api.json().get("resposta", "Desculpe, não consegui obter uma resposta da IA.")

        else:
            return f"Erro na API: {resposta_api.status_code}"

    except Exception as ex:
        return f"Erro de conexão com o servidor local: {ex}. A API está rodando?"
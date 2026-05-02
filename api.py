from fastapi import FastAPI
from pydantic import BaseModel
from src.services.llm_service import gerar_resposta_ia, extrair_vetores_da_conversa
from src.services.database import salvar_perfil_usuario, buscar_melhor_match, popular_banco_mock
from src.services.sqlite_db import iniciar_banco_sqlite, salvar_mensagem, salvar_vetores_sqlite, obter_historico_chat

app = FastAPI(
    title="MatchAI API",
    description="Backend para o aplicativo de relacionamento",
    version="0.1.0"
)

popular_banco_mock()
iniciar_banco_sqlite() 

class MensagemUsuario(BaseModel):
    texto: str

@app.get("/")
def read_root():
    return {"mensagem": "API do MatchAI está a correr perfeitamente!"}

@app.get("/historico")
def pegar_historico():
    # Nova rota que envia o histórico salvo para o aplicativo Flet
    historico = obter_historico_chat(usuario="user_rafaell")
    return {"historico": historico}

@app.post("/chat")
def conversar_com_ia(mensagem: MensagemUsuario):
    salvar_mensagem(usuario="user_rafaell", remetente="usuario", mensagem=mensagem.texto)
    resposta = gerar_resposta_ia(mensagem.texto)
    salvar_mensagem(usuario="user_rafaell", remetente="ia", mensagem=resposta)
    return {"resposta": resposta}

@app.post("/analisar_perfil")
def analisar_perfil(mensagem: MensagemUsuario):
    vetores_json = extrair_vetores_da_conversa(mensagem.texto)
    return {
        "texto_analisado": mensagem.texto,
        "vetores_calculados": vetores_json
    }

@app.post("/dar_match")
def calcular_match_final(mensagem: MensagemUsuario):
    texto_recebido = mensagem.texto.strip()

    if not texto_recebido:
        historico = obter_historico_chat(usuario="user_rafaell")

        mensagens_usuario = [
            item["mensagem"]
            for item in historico
            if item["remetente"] == "usuario"
        ]

        texto_recebido = "\n".join(mensagens_usuario)

    if not texto_recebido:
        return {
            "sucesso": False,
            "mensagem": "Ainda não há conversa suficiente para calcular um match."
        }

    vetores_json = extrair_vetores_da_conversa(texto_recebido)

    if not vetores_json:
        return {
            "sucesso": False,
            "mensagem": "Não foi possível extrair vetores da conversa."
        }

    salvar_vetores_sqlite(usuario="user_rafaell", vetores_dict=vetores_json)

    vetor_calculado = salvar_perfil_usuario(
        "user_rafaell",
        "Rafaell",
        vetores_json
    )

    melhores_matches = buscar_melhor_match(
        "user_rafaell",
        vetor_calculado,
        quantidade=1
    )

    if melhores_matches:
        return {
            "sucesso": True,
            "match": melhores_matches[0]
        }

    return {
        "sucesso": False,
        "mensagem": "Nenhum match encontrado."
    }
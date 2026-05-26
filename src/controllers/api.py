from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from src.services.database import (
    buscar_melhor_match,
    popular_banco_mock,
    salvar_perfil_usuario,
)
from src.services.llm_service import gerar_resposta_ia, extrair_vetores_da_conversa
from src.services.sqlite_db import (
    iniciar_banco_sqlite,
    obter_historico_chat,
    salvar_mensagem,
    salvar_vetores_sqlite,
)


USUARIO_PADRAO = "user_rafaell"
NOME_USUARIO_PADRAO = "Rafaell"


@asynccontextmanager
async def lifespan(app: FastAPI):
    popular_banco_mock()
    iniciar_banco_sqlite()
    yield


app = FastAPI(
    title="MatchAI API",
    description="Backend para o aplicativo de relacionamento",
    version="0.1.0",
    lifespan=lifespan,
)


class MensagemUsuario(BaseModel):
    texto: str


@app.get("/")
def read_root():
    return {"mensagem": "API do MatchAI esta rodando perfeitamente!"}


@app.get("/historico")
def pegar_historico():
    historico = obter_historico_chat(usuario=USUARIO_PADRAO)
    return {"historico": historico}


@app.post("/chat")
def conversar_com_ia(mensagem: MensagemUsuario):
    salvar_mensagem(
        usuario=USUARIO_PADRAO,
        remetente="usuario",
        mensagem=mensagem.texto,
    )
    resposta = gerar_resposta_ia(mensagem.texto)
    salvar_mensagem(
        usuario=USUARIO_PADRAO,
        remetente="ia",
        mensagem=resposta,
    )
    return {"resposta": resposta}


@app.post("/analisar_perfil")
def analisar_perfil(mensagem: MensagemUsuario):
    vetores_json = extrair_vetores_da_conversa(mensagem.texto)
    return {
        "texto_analisado": mensagem.texto,
        "vetores_calculados": vetores_json,
    }


@app.post("/dar_match")
def calcular_match_final(mensagem: MensagemUsuario):
    texto_recebido = mensagem.texto.strip()

    if not texto_recebido:
        historico = obter_historico_chat(usuario=USUARIO_PADRAO)
        mensagens_usuario = [
            item["mensagem"]
            for item in historico
            if item["remetente"] == "usuario"
        ]
        texto_recebido = "\n".join(mensagens_usuario)

    if not texto_recebido:
        return {
            "sucesso": False,
            "mensagem": "Ainda nao ha conversa suficiente para calcular um match.",
        }

    vetores_json = extrair_vetores_da_conversa(texto_recebido)

    if not vetores_json:
        return {
            "sucesso": False,
            "mensagem": "Nao foi possivel extrair vetores da conversa.",
        }

    salvar_vetores_sqlite(usuario=USUARIO_PADRAO, vetores_dict=vetores_json)

    vetor_calculado = salvar_perfil_usuario(
        USUARIO_PADRAO,
        NOME_USUARIO_PADRAO,
        vetores_json,
    )

    melhores_matches = buscar_melhor_match(
        USUARIO_PADRAO,
        vetor_calculado,
        quantidade=1,
    )

    if melhores_matches:
        return {
            "sucesso": True,
            "match": melhores_matches[0],
        }

    return {
        "sucesso": False,
        "mensagem": "Nenhum match encontrado.",
    }

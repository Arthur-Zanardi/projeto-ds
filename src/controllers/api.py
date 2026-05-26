import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from src.services.database import (
    buscar_melhor_match,
    popular_banco_mock,
    salvar_perfil_usuario,
)
from src.services.llm_service import (
    LLMServiceError,
    gerar_resposta_ia,
    extrair_vetores_da_conversa,
)
from src.services.sqlite_db import (
    iniciar_banco_sqlite,
    obter_historico_chat,
    obter_logs_api,
    registrar_log_api,
    salvar_mensagem,
    salvar_vetores_sqlite,
)


USUARIO_PADRAO = "user_rafaell"
NOME_USUARIO_PADRAO = "Rafaell"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class MensagemTextoObrigatorio(BaseModel):
    texto: str

    @field_validator("texto")
    @classmethod
    def texto_nao_pode_ser_vazio(cls, texto):
        texto = texto.strip()

        if not texto:
            raise ValueError("O campo texto nao pode ser vazio.")

        return texto


class MensagemMatch(BaseModel):
    texto: str = ""

    @field_validator("texto")
    @classmethod
    def normalizar_texto(cls, texto):
        return texto.strip()


def registrar_evento(
    endpoint: str,
    acao: str,
    status: str,
    mensagem: str,
    detalhes: dict | None = None,
):
    if status == "erro":
        logger.error("%s | %s | %s", endpoint, acao, mensagem)
    else:
        logger.info("%s | %s | %s", endpoint, acao, mensagem)

    try:
        registrar_log_api(
            usuario=USUARIO_PADRAO,
            endpoint=endpoint,
            acao=acao,
            status=status,
            mensagem=mensagem,
            detalhes=detalhes,
        )
    except Exception:
        logger.exception("Falha ao registrar log da API no SQLite.")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    erros = jsonable_encoder(exc.errors())
    registrar_evento(
        endpoint=request.url.path,
        acao="validacao",
        status="erro",
        mensagem="Entrada invalida.",
        detalhes={"erros": erros},
    )
    return JSONResponse(status_code=422, content={"detail": erros})


@app.get("/")
def read_root():
    return {"mensagem": "API do MatchAI esta rodando perfeitamente!"}


@app.get("/historico")
def pegar_historico():
    try:
        historico = obter_historico_chat(usuario=USUARIO_PADRAO)
        registrar_evento(
            endpoint="/historico",
            acao="buscar_historico",
            status="sucesso",
            mensagem="Historico carregado.",
            detalhes={"total_mensagens": len(historico)},
        )
        return {"historico": historico}
    except Exception as erro:
        registrar_evento(
            endpoint="/historico",
            acao="buscar_historico",
            status="erro",
            mensagem="Falha ao carregar historico.",
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel carregar o historico.",
        ) from erro


@app.get("/logs")
def pegar_logs():
    try:
        logs = obter_logs_api(usuario=USUARIO_PADRAO)
        return {"logs": logs}
    except Exception as erro:
        logger.exception("Falha ao carregar logs da API.")
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel carregar os logs.",
        ) from erro


@app.post("/chat")
def conversar_com_ia(mensagem: MensagemTextoObrigatorio):
    registrar_evento(
        endpoint="/chat",
        acao="receber_mensagem",
        status="iniciado",
        mensagem="Mensagem recebida.",
    )

    try:
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
        registrar_evento(
            endpoint="/chat",
            acao="responder_ia",
            status="sucesso",
            mensagem="Resposta da IA gerada e salva.",
        )
        return {"resposta": resposta}
    except LLMServiceError as erro:
        registrar_evento(
            endpoint="/chat",
            acao="responder_ia",
            status="erro",
            mensagem="Falha ao gerar resposta da IA.",
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel gerar resposta da IA.",
        ) from erro
    except Exception as erro:
        registrar_evento(
            endpoint="/chat",
            acao="processar_chat",
            status="erro",
            mensagem="Falha ao processar chat.",
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Falha interna ao processar chat.",
        ) from erro


@app.post("/analisar_perfil")
def analisar_perfil(mensagem: MensagemTextoObrigatorio):
    try:
        vetores_json = extrair_vetores_da_conversa(mensagem.texto)
        registrar_evento(
            endpoint="/analisar_perfil",
            acao="extrair_vetores",
            status="sucesso",
            mensagem="Vetores extraidos da conversa.",
        )
        return {
            "texto_analisado": mensagem.texto,
            "vetores_calculados": vetores_json,
        }
    except LLMServiceError as erro:
        registrar_evento(
            endpoint="/analisar_perfil",
            acao="extrair_vetores",
            status="erro",
            mensagem="Falha ao extrair vetores.",
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel extrair vetores da conversa.",
        ) from erro


@app.post("/dar_match")
def calcular_match_final(mensagem: MensagemMatch):
    texto_recebido = mensagem.texto

    try:
        if not texto_recebido:
            historico = obter_historico_chat(usuario=USUARIO_PADRAO)
            mensagens_usuario = [
                item["mensagem"]
                for item in historico
                if item["remetente"] == "usuario"
            ]
            texto_recebido = "\n".join(mensagens_usuario)

        if not texto_recebido:
            registrar_evento(
                endpoint="/dar_match",
                acao="calcular_match",
                status="sem_dados",
                mensagem="Conversa insuficiente para calcular match.",
            )
            return {
                "sucesso": False,
                "mensagem": "Ainda nao ha conversa suficiente para calcular um match.",
            }

        vetores_json = extrair_vetores_da_conversa(texto_recebido)
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
            registrar_evento(
                endpoint="/dar_match",
                acao="calcular_match",
                status="sucesso",
                mensagem="Match calculado.",
                detalhes={
                    "match": melhores_matches[0]["id"],
                    "dimensoes_comparadas": melhores_matches[0].get(
                        "dimensoes_comparadas"
                    ),
                },
            )
            return {
                "sucesso": True,
                "match": melhores_matches[0],
            }

        registrar_evento(
            endpoint="/dar_match",
            acao="calcular_match",
            status="sem_match",
            mensagem="Nenhum match encontrado.",
        )
        return {
            "sucesso": False,
            "mensagem": "Nenhum match encontrado.",
        }
    except LLMServiceError as erro:
        registrar_evento(
            endpoint="/dar_match",
            acao="extrair_vetores",
            status="erro",
            mensagem="Falha ao extrair vetores para match.",
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel extrair vetores para calcular o match.",
        ) from erro
    except Exception as erro:
        registrar_evento(
            endpoint="/dar_match",
            acao="calcular_match",
            status="erro",
            mensagem="Falha ao calcular match.",
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Falha interna ao calcular match.",
        ) from erro

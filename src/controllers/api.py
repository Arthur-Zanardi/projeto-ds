import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.services.database import (
    achatar_dados_vetoriais,
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
    criar_match_usuario,
    iniciar_banco_sqlite,
    listar_matches_usuario,
    obter_historico_chat,
    obter_historico_match,
    obter_match_usuario,
    obter_ultimo_vetor_sqlite,
    obter_logs_api,
    registrar_log_api,
    salvar_mensagem,
    salvar_mensagem_match,
    salvar_vetores_sqlite,
)
from src.services.user_context import (
    normalizar_email_usuario,
    normalizar_nome_usuario,
    usuario_eh_admin,
)


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


class CriarMatchRequisicao(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    match_id: str = Field(alias="id")
    nome: str
    afinidade: str | None = None
    dados_match: dict | None = None

    @field_validator("match_id", "nome")
    @classmethod
    def campo_nao_pode_ser_vazio(cls, valor):
        valor = str(valor).strip()

        if not valor:
            raise ValueError("O campo nao pode ser vazio.")

        return valor

    def dados_para_salvar(self):
        if self.dados_match is not None:
            return self.dados_match

        dados = {
            "match_id": self.match_id,
            "nome": self.nome,
            "afinidade": self.afinidade,
        }
        dados.update(self.model_extra or {})
        return dados


class MensagemConversaMatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    texto: str = Field(alias="mensagem")
    remetente: str = "usuario"

    @field_validator("texto", "remetente")
    @classmethod
    def texto_nao_pode_ser_vazio(cls, texto):
        texto = texto.strip()

        if not texto:
            raise ValueError("O campo nao pode ser vazio.")

        return texto


def obter_usuario_atual(
    x_usuario_email=None,
    x_usuario_nome=None,
):
    if not isinstance(x_usuario_email, str):
        x_usuario_email = None

    if not isinstance(x_usuario_nome, str):
        x_usuario_nome = None

    email = normalizar_email_usuario(x_usuario_email)
    nome = normalizar_nome_usuario(x_usuario_nome, email)
    return {"email": email, "nome": nome}


def obter_usuario_request(request: Request):
    return obter_usuario_atual(
        x_usuario_email=request.headers.get("X-Usuario-Email"),
        x_usuario_nome=request.headers.get("X-Usuario-Nome"),
    )


def match_eh_mock_customizado(match: CriarMatchRequisicao):
    dados_match = match.dados_para_salvar()
    return (
        match.match_id.startswith("custom_")
        or bool(dados_match.get("mock_customizado"))
        or bool(dados_match.get("custom_mock"))
    )


def registrar_evento(
    endpoint: str,
    acao: str,
    status: str,
    mensagem: str,
    usuario: str | None = None,
    detalhes: dict | None = None,
):
    if status == "erro":
        logger.error("%s | %s | %s", endpoint, acao, mensagem)
    else:
        logger.info("%s | %s | %s", endpoint, acao, mensagem)

    try:
        registrar_log_api(
            usuario=normalizar_email_usuario(usuario),
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
        usuario=obter_usuario_request(request)["email"],
        detalhes={"erros": erros},
    )
    return JSONResponse(status_code=422, content={"detail": erros})


@app.get("/")
def read_root():
    return {"mensagem": "API do MatchAI esta rodando perfeitamente!"}


@app.get("/historico")
def pegar_historico(
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        historico = obter_historico_chat(usuario=usuario_atual["email"])
        registrar_evento(
            endpoint="/historico",
            acao="buscar_historico",
            status="sucesso",
            mensagem="Historico carregado.",
            usuario=usuario_atual["email"],
            detalhes={"total_mensagens": len(historico)},
        )
        return {"historico": historico}
    except Exception as erro:
        registrar_evento(
            endpoint="/historico",
            acao="buscar_historico",
            status="erro",
            mensagem="Falha ao carregar historico.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel carregar o historico.",
        ) from erro


@app.get("/logs")
def pegar_logs(
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        logs = obter_logs_api(usuario=usuario_atual["email"])
        return {"logs": logs}
    except Exception as erro:
        logger.exception("Falha ao carregar logs da API.")
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel carregar os logs.",
        ) from erro


@app.get("/matches")
def pegar_matches(
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        matches = listar_matches_usuario(usuario=usuario_atual["email"])
        registrar_evento(
            endpoint="/matches",
            acao="listar_matches",
            status="sucesso",
            mensagem="Matches carregados.",
            usuario=usuario_atual["email"],
            detalhes={"total_matches": len(matches)},
        )
        return {"matches": matches}
    except Exception as erro:
        registrar_evento(
            endpoint="/matches",
            acao="listar_matches",
            status="erro",
            mensagem="Falha ao carregar matches.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel carregar os matches.",
        ) from erro


@app.post("/matches", status_code=201)
def criar_match_api(
    match: CriarMatchRequisicao,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        if match_eh_mock_customizado(match) and not usuario_eh_admin(
            usuario_atual["email"]
        ):
            registrar_evento(
                endpoint="/matches",
                acao="criar_match",
                status="erro",
                mensagem="Usuario sem permissao para criar mock customizado.",
                usuario=usuario_atual["email"],
                detalhes={"match_id": match.match_id},
            )
            raise HTTPException(
                status_code=403,
                detail="Apenas administradores podem criar perfis mock.",
            )

        match_salvo = criar_match_usuario(
            usuario=usuario_atual["email"],
            match_id=match.match_id,
            nome=match.nome,
            afinidade=match.afinidade,
            dados_match=match.dados_para_salvar(),
        )
        registrar_evento(
            endpoint="/matches",
            acao="criar_match",
            status="sucesso",
            mensagem="Match salvo.",
            usuario=usuario_atual["email"],
            detalhes={"match_id": match.match_id},
        )
        return {"match": match_salvo}
    except HTTPException:
        raise
    except Exception as erro:
        registrar_evento(
            endpoint="/matches",
            acao="criar_match",
            status="erro",
            mensagem="Falha ao salvar match.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel salvar o match.",
        ) from erro


@app.get("/matches/{match_id}/mensagens")
def pegar_mensagens_match(
    match_id: str,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        match = obter_match_usuario(usuario=usuario_atual["email"], match_id=match_id)

        if match is None:
            registrar_evento(
                endpoint=f"/matches/{match_id}/mensagens",
                acao="listar_mensagens_match",
                status="nao_encontrado",
                mensagem="Match nao encontrado.",
                usuario=usuario_atual["email"],
                detalhes={"match_id": match_id},
            )
            raise HTTPException(
                status_code=404,
                detail="Match nao encontrado.",
            )

        mensagens = obter_historico_match(
            usuario=usuario_atual["email"],
            match_id=match_id,
        )
        registrar_evento(
            endpoint=f"/matches/{match_id}/mensagens",
            acao="listar_mensagens_match",
            status="sucesso",
            mensagem="Mensagens do match carregadas.",
            usuario=usuario_atual["email"],
            detalhes={"match_id": match_id, "total_mensagens": len(mensagens)},
        )
        return {"match_id": match_id, "mensagens": mensagens}
    except HTTPException:
        raise
    except Exception as erro:
        registrar_evento(
            endpoint=f"/matches/{match_id}/mensagens",
            acao="listar_mensagens_match",
            status="erro",
            mensagem="Falha ao carregar mensagens do match.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro), "match_id": match_id},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel carregar as mensagens do match.",
        ) from erro


@app.post("/matches/{match_id}/mensagens", status_code=201)
def enviar_mensagem_match(
    match_id: str,
    mensagem: MensagemConversaMatch,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        salvar_mensagem_match(
            usuario=usuario_atual["email"],
            match_id=match_id,
            remetente=mensagem.remetente,
            mensagem=mensagem.texto,
        )
        registrar_evento(
            endpoint=f"/matches/{match_id}/mensagens",
            acao="enviar_mensagem_match",
            status="sucesso",
            mensagem="Mensagem do match salva.",
            usuario=usuario_atual["email"],
            detalhes={"match_id": match_id, "remetente": mensagem.remetente},
        )
        return {
            "sucesso": True,
            "mensagem": {
                "match_id": match_id,
                "remetente": mensagem.remetente,
                "mensagem": mensagem.texto,
            },
        }
    except ValueError as erro:
        registrar_evento(
            endpoint=f"/matches/{match_id}/mensagens",
            acao="enviar_mensagem_match",
            status="nao_encontrado",
            mensagem="Match nao encontrado.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro), "match_id": match_id},
        )
        raise HTTPException(
            status_code=404,
            detail="Match nao encontrado.",
        ) from erro
    except Exception as erro:
        registrar_evento(
            endpoint=f"/matches/{match_id}/mensagens",
            acao="enviar_mensagem_match",
            status="erro",
            mensagem="Falha ao salvar mensagem do match.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro), "match_id": match_id},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel salvar a mensagem do match.",
        ) from erro


@app.post("/chat")
def conversar_com_ia(
    mensagem: MensagemTextoObrigatorio,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    registrar_evento(
        endpoint="/chat",
        acao="receber_mensagem",
        status="iniciado",
        mensagem="Mensagem recebida.",
        usuario=usuario_atual["email"],
    )

    try:
        etapa_ia = "gerar_resposta"
        salvar_mensagem(
            usuario=usuario_atual["email"],
            remetente="usuario",
            mensagem=mensagem.texto,
        )
        resposta = gerar_resposta_ia(mensagem.texto)
        salvar_mensagem(
            usuario=usuario_atual["email"],
            remetente="ia",
            mensagem=resposta,
        )

        historico = obter_historico_chat(usuario=usuario_atual["email"])
        mensagens_usuario = [
            item["mensagem"]
            for item in historico
            if item["remetente"] == "usuario"
        ]
        texto_perfil = "\n".join(mensagens_usuario)

        etapa_ia = "atualizar_perfil"
        vetores_json = extrair_vetores_da_conversa(texto_perfil)
        salvar_vetores_sqlite(
            usuario=usuario_atual["email"],
            vetores_dict=vetores_json,
        )
        salvar_perfil_usuario(
            usuario_atual["email"],
            usuario_atual["nome"],
            vetores_json,
        )

        registrar_evento(
            endpoint="/chat",
            acao="responder_ia",
            status="sucesso",
            mensagem="Resposta da IA gerada e perfil vetorial atualizado.",
            usuario=usuario_atual["email"],
        )
        return {"resposta": resposta, "perfil_atualizado": True}
    except LLMServiceError as erro:
        detail = (
            "Nao foi possivel atualizar o perfil vetorial."
            if etapa_ia == "atualizar_perfil"
            else "Nao foi possivel gerar resposta da IA."
        )
        registrar_evento(
            endpoint="/chat",
            acao=etapa_ia,
            status="erro",
            mensagem=detail,
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail=detail,
        ) from erro
    except Exception as erro:
        registrar_evento(
            endpoint="/chat",
            acao="processar_chat",
            status="erro",
            mensagem="Falha ao processar chat.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Falha interna ao processar chat.",
        ) from erro


@app.post("/analisar_perfil")
def analisar_perfil(
    mensagem: MensagemTextoObrigatorio,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        vetores_json = extrair_vetores_da_conversa(mensagem.texto)
        registrar_evento(
            endpoint="/analisar_perfil",
            acao="extrair_vetores",
            status="sucesso",
            mensagem="Vetores extraidos da conversa.",
            usuario=usuario_atual["email"],
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
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel extrair vetores da conversa.",
        ) from erro


@app.post("/dar_match")
def calcular_match_final(
    mensagem: MensagemMatch,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        vetores_json = obter_ultimo_vetor_sqlite(usuario=usuario_atual["email"])

        if not vetores_json:
            registrar_evento(
                endpoint="/dar_match",
                acao="calcular_match",
                status="sem_dados",
                mensagem="Perfil vetorial inexistente para calcular match.",
                usuario=usuario_atual["email"],
            )
            return {
                "sucesso": False,
                "mensagem": "Ainda nao ha perfil vetorial salvo para calcular um match.",
            }

        vetor_calculado = achatar_dados_vetoriais(vetores_json)

        melhores_matches = buscar_melhor_match(
            usuario_atual["email"],
            vetor_calculado,
            quantidade=1,
        )

        if melhores_matches:
            registrar_evento(
                endpoint="/dar_match",
                acao="calcular_match",
                status="sucesso",
                mensagem="Match calculado.",
                usuario=usuario_atual["email"],
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
            usuario=usuario_atual["email"],
        )
        return {
            "sucesso": False,
            "mensagem": "Nenhum match encontrado.",
        }
    except Exception as erro:
        registrar_evento(
            endpoint="/dar_match",
            acao="calcular_match",
            status="erro",
            mensagem="Falha ao calcular match.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(
            status_code=503,
            detail="Falha interna ao calcular match.",
        ) from erro

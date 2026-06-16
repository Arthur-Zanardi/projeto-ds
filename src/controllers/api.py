import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.services.conversation_starters import gerar_sugestoes_inicio
from src.services.database import (
    achatar_dados_vetoriais,
    buscar_melhor_match,
    calcular_dimensoes_mais_proximas,
    criar_vetor_mock_padrao,
    obter_vetor_usuario,
    salvar_perfil_usuario,
    salvar_perfil_vetorial,
)
from src.services.llm_service import (
    LLMServiceError,
    extrair_vetores_da_conversa,
    gerar_resposta_ia,
)
from src.services.profile_completion import (
    anexar_status_perfil,
    campos_faltantes_perfil,
    perfil_publico_completo,
)
from src.services.postgres_db import (
    confirmar_match,
    criar_match_usuario,
    listar_ids_indisponiveis_match,
    listar_matches_usuario,
    listar_perfis_publicos,
    obter_acao_match,
    obter_historico_chat,
    obter_historico_match,
    obter_logs_api,
    obter_match_usuario,
    obter_perfil_publico,
    obter_ultimo_vetor_sqlite,
    registrar_acao_match,
    registrar_log_api,
    salvar_mensagem,
    salvar_mensagem_match,
    salvar_perfil_publico,
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
    # O esquema do banco é criado/evoluído apenas via Alembic.
    # O seed de perfis mock é feito pelo entrypoint/scripts (dev).
    yield


app = FastAPI(
    title="MatchAI API",
    description="Backend para o aplicativo de relacionamento",
    version="0.2.0",
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


class PerfilPublicoPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    nome: str | None = None
    idade: int | str | None = None
    foto_url: str | None = None
    imagem: str | None = None
    descricao: str | None = None
    localizacao: str | None = None
    cargo: str | None = None

    def foto_final(self):
        return self.foto_url or self.imagem


class CriarPerfilMockRequisicao(PerfilPublicoPayload):
    id: str | None = None
    nome: str
    vetores: dict | None = None

    @field_validator("nome")
    @classmethod
    def nome_obrigatorio(cls, valor):
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("Nome do perfil mock e obrigatorio.")
        return valor


class AcaoMatchRequisicao(BaseModel):
    acao: str

    @field_validator("acao")
    @classmethod
    def acao_valida(cls, valor):
        valor = (valor or "").strip().lower()
        if valor not in {"like", "pass"}:
            raise ValueError("Acao precisa ser like ou pass.")
        return valor


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

        dados = {"match_id": self.match_id, "nome": self.nome}
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


def obter_usuario_atual(x_usuario_email=None, x_usuario_nome=None):
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


def slugify(texto: str):
    slug = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")
    return slug or "perfil"


def nome_por_identificador(identificador: str):
    identificador = str(identificador or "").strip()

    if "@" in identificador:
        return normalizar_nome_usuario(None, identificador)

    for prefixo in ("custom_", "user_", "mock_"):
        if identificador.startswith(prefixo):
            identificador = identificador[len(prefixo):]
            break

    partes = [
        parte
        for parte in re.split(r"[_\-.]+", identificador)
        if parte and not re.fullmatch(r"[0-9a-f]{4,}", parte)
    ]
    return " ".join(partes).title() or "Perfil"


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


def perfil_publico_ou_padrao(usuario: dict):
    perfil = obter_perfil_publico(usuario["email"])
    if perfil:
        return perfil

    return salvar_perfil_publico(
        usuario=usuario["email"],
        nome=usuario["nome"],
        origem="real",
        mock_customizado=False,
    )


def limpar_dados_visiveis(perfil: dict):
    dados = dict(perfil or {})
    dados.pop("afinidade", None)
    dados.pop("score_interno", None)
    dados.pop("distancia_matematica", None)
    dados.pop("dimensoes_comparadas", None)
    dados.pop("vetor_candidato", None)
    return dados


def montar_candidato(match_vetorial: dict):
    match_id = match_vetorial.get("id")
    perfil = obter_perfil_publico(match_id) or {
        "id": match_id,
        "match_id": match_id,
        "usuario": match_id,
        "nome": match_vetorial.get("nome", "Perfil"),
        "idade": None,
        "imagem": None,
        "foto_url": None,
        "descricao": "Perfil construido a partir da entrevista.",
        "localizacao": "",
        "cargo": "",
        "origem": "real" if "@" in str(match_id) else "mock",
        "mock_customizado": False,
    }
    candidato = {**perfil, **match_vetorial}
    candidato["id"] = match_id
    candidato["match_id"] = match_id
    candidato["nome"] = perfil.get("nome") or match_vetorial.get("nome")
    candidato["imagem"] = perfil.get("imagem") or perfil.get("foto_url")
    candidato["tipo"] = perfil.get("origem", "real")
    return limpar_dados_visiveis(candidato)


def candidato_eh_mock(perfil: dict):
    return (
        perfil.get("origem") == "mock"
        or perfil.get("mock_customizado") is True
        or str(perfil.get("id") or "").startswith(("user_", "custom_"))
    )


def perfil_candidato_ou_padrao(match_id: str):
    perfil = obter_perfil_publico(match_id)
    if perfil is not None:
        return perfil

    mock = str(match_id).startswith(("user_", "custom_", "mock_")) or "@" not in str(match_id)
    return salvar_perfil_publico(
        usuario=match_id,
        nome=nome_por_identificador(match_id),
        origem="mock" if mock else "real",
        mock_customizado=str(match_id).startswith("custom_"),
    )


def gerar_sugestoes_para_match(usuario_email: str, candidato_id: str, vetor_usuario: list | None):
    if vetor_usuario is None:
        vetores_json = obter_ultimo_vetor_sqlite(usuario=usuario_email)
        vetor_usuario = achatar_dados_vetoriais(vetores_json) if vetores_json else None

    vetor_candidato = obter_vetor_usuario(candidato_id)

    if not vetor_usuario or not vetor_candidato:
        return []

    dimensoes = calcular_dimensoes_mais_proximas(vetor_usuario, vetor_candidato, quantidade=3)
    return gerar_sugestoes_inicio(dimensoes)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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


@app.get("/perfil_publico")
def pegar_perfil_publico(
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)
    return {"perfil": anexar_status_perfil(perfil_publico_ou_padrao(usuario_atual))}


@app.put("/perfil_publico")
def atualizar_perfil_publico(
    perfil: PerfilPublicoPayload,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)
    perfil_salvo = salvar_perfil_publico(
        usuario=usuario_atual["email"],
        nome=perfil.nome or usuario_atual["nome"],
        idade=perfil.idade,
        foto_url=perfil.foto_final(),
        descricao=perfil.descricao,
        localizacao=perfil.localizacao,
        cargo=perfil.cargo,
        origem="real",
        mock_customizado=False,
    )
    return {"perfil": anexar_status_perfil(perfil_salvo)}


@app.post("/perfis_mock", status_code=201)
def criar_perfil_mock(
    perfil: CriarPerfilMockRequisicao,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    if not usuario_eh_admin(usuario_atual["email"]):
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem criar perfis mock.",
        )

    perfil_id = perfil.id or f"custom_{slugify(perfil.nome)}_{uuid.uuid4().hex[:6]}"
    perfil_salvo = salvar_perfil_publico(
        usuario=perfil_id,
        nome=perfil.nome,
        idade=perfil.idade,
        foto_url=perfil.foto_final(),
        descricao=perfil.descricao,
        localizacao=perfil.localizacao,
        cargo=perfil.cargo,
        origem="mock",
        mock_customizado=True,
    )
    vetores = perfil.vetores or criar_vetor_mock_padrao(perfil_id)
    salvar_perfil_vetorial(perfil_id, perfil.nome, vetores)

    registrar_evento(
        endpoint="/perfis_mock",
        acao="criar_mock",
        status="sucesso",
        mensagem="Perfil mock criado.",
        usuario=usuario_atual["email"],
        detalhes={"perfil_id": perfil_id},
    )
    return {"perfil": perfil_salvo}


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
        raise HTTPException(status_code=503, detail="Nao foi possivel carregar o historico.") from erro


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
        raise HTTPException(status_code=503, detail="Nao foi possivel carregar os logs.") from erro


@app.get("/matches")
def pegar_matches(
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        matches = [limpar_dados_visiveis(match) for match in listar_matches_usuario(usuario=usuario_atual["email"])]
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
        raise HTTPException(status_code=503, detail="Nao foi possivel carregar os matches.") from erro


@app.post("/matches", status_code=201)
def criar_match_api(
    match: CriarMatchRequisicao,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        if match_eh_mock_customizado(match) and not usuario_eh_admin(usuario_atual["email"]):
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
        return {"match": limpar_dados_visiveis(match_salvo)}
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
        raise HTTPException(status_code=503, detail="Nao foi possivel salvar o match.") from erro


@app.post("/matches/{match_id}/acao")
def registrar_acao_match_api(
    match_id: str,
    acao: AcaoMatchRequisicao,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)
    usuario_email = usuario_atual["email"]
    match_id = str(match_id or "").strip().lower()

    if not match_id or match_id == usuario_email:
        raise HTTPException(status_code=400, detail="Candidato invalido.")

    acao_salva = registrar_acao_match(usuario_email, match_id, acao.acao)

    if acao.acao == "pass":
        return {
            "status": "recusado",
            "match_confirmado": False,
            "acao": acao_salva,
        }

    perfil_candidato = perfil_candidato_ou_padrao(match_id)
    perfil_usuario = perfil_publico_ou_padrao(usuario_atual)
    mock = candidato_eh_mock(perfil_candidato)
    acao_reciproca = obter_acao_match(match_id, usuario_email)
    reciprocou = bool(acao_reciproca and acao_reciproca["acao"] == "like")

    if not mock and not reciprocou:
        return {
            "status": "pendente",
            "match_confirmado": False,
            "mensagem": "Like salvo. A conversa abre quando a outra pessoa tambem der match.",
        }

    vetores_json = obter_ultimo_vetor_sqlite(usuario_email)
    vetor_usuario = achatar_dados_vetoriais(vetores_json) if vetores_json else None
    sugestoes = gerar_sugestoes_para_match(usuario_email, match_id, vetor_usuario)
    match_salvo = confirmar_match(
        usuario=usuario_email,
        candidato_id=match_id,
        perfil_candidato=perfil_candidato,
        perfil_usuario=perfil_usuario,
        tipo="mock" if mock else "real",
        sugestoes=sugestoes,
    )

    return {
        "status": "confirmado",
        "match_confirmado": True,
        "match": limpar_dados_visiveis(match_salvo),
        "sugestoes": sugestoes,
    }


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
                mensagem="Match nao confirmado.",
                usuario=usuario_atual["email"],
                detalhes={"match_id": match_id},
            )
            raise HTTPException(status_code=404, detail="Match nao encontrado.")

        mensagens = obter_historico_match(usuario=usuario_atual["email"], match_id=match_id)
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
        raise HTTPException(status_code=503, detail="Nao foi possivel carregar as mensagens do match.") from erro


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
            mensagem="Match nao confirmado.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro), "match_id": match_id},
        )
        raise HTTPException(status_code=404, detail="Match nao encontrado.") from erro
    except Exception as erro:
        registrar_evento(
            endpoint=f"/matches/{match_id}/mensagens",
            acao="enviar_mensagem_match",
            status="erro",
            mensagem="Falha ao salvar mensagem do match.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro), "match_id": match_id},
        )
        raise HTTPException(status_code=503, detail="Nao foi possivel salvar a mensagem do match.") from erro


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
        salvar_mensagem(usuario=usuario_atual["email"], remetente="usuario", mensagem=mensagem.texto)
        resposta = gerar_resposta_ia(mensagem.texto)
        salvar_mensagem(usuario=usuario_atual["email"], remetente="ia", mensagem=resposta)

        historico = obter_historico_chat(usuario=usuario_atual["email"])
        mensagens_usuario = [
            item["mensagem"]
            for item in historico
            if item["remetente"] == "usuario"
        ]
        texto_perfil = "\n".join(mensagens_usuario)

        etapa_ia = "atualizar_perfil"
        vetores_json = extrair_vetores_da_conversa(texto_perfil)
        salvar_vetores_sqlite(usuario=usuario_atual["email"], vetores_dict=vetores_json)
        perfil = perfil_publico_ou_padrao(usuario_atual)
        salvar_perfil_usuario(usuario_atual["email"], perfil["nome"], vetores_json)

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
        raise HTTPException(status_code=503, detail=detail) from erro
    except Exception as erro:
        registrar_evento(
            endpoint="/chat",
            acao="processar_chat",
            status="erro",
            mensagem="Falha ao processar chat.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(status_code=503, detail="Falha interna ao processar chat.") from erro


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
        return {"texto_analisado": mensagem.texto, "vetores_calculados": vetores_json}
    except LLMServiceError as erro:
        registrar_evento(
            endpoint="/analisar_perfil",
            acao="extrair_vetores",
            status="erro",
            mensagem="Falha ao extrair vetores.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(status_code=503, detail="Nao foi possivel extrair vetores da conversa.") from erro


@app.post("/dar_match")
def calcular_match_final(
    mensagem: MensagemMatch,
    x_usuario_email: str | None = Header(default=None, alias="X-Usuario-Email"),
    x_usuario_nome: str | None = Header(default=None, alias="X-Usuario-Nome"),
):
    usuario_atual = obter_usuario_atual(x_usuario_email, x_usuario_nome)

    try:
        perfil_publico = perfil_publico_ou_padrao(usuario_atual)
        if not perfil_publico_completo(perfil_publico):
            faltantes = campos_faltantes_perfil(perfil_publico)
            registrar_evento(
                endpoint="/dar_match",
                acao="calcular_match",
                status="perfil_incompleto",
                mensagem="Perfil publico incompleto para descobrir matches.",
                usuario=usuario_atual["email"],
                detalhes={"campos_faltantes": faltantes},
            )
            return {
                "sucesso": False,
                "perfil_incompleto": True,
                "campos_faltantes": faltantes,
                "mensagem": "Complete seu perfil antes de descobrir matches.",
            }

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
        ignorados = listar_ids_indisponiveis_match(usuario_atual["email"])
        try:
            melhores_matches = buscar_melhor_match(
                usuario_atual["email"],
                vetor_calculado,
                quantidade=20,
                ids_ignorados=ignorados,
                incluir_vetor=True,
            )
        except TypeError:
            melhores_matches = buscar_melhor_match(
                usuario_atual["email"],
                vetor_calculado,
                quantidade=20,
            )

        candidatos = []
        for match in melhores_matches:
            candidato = montar_candidato(match)
            if candidato["id"] == usuario_atual["email"]:
                continue
            candidatos.append(candidato)

        if candidatos:
            registrar_evento(
                endpoint="/dar_match",
                acao="calcular_match",
                status="sucesso",
                mensagem="Deck de matches calculado.",
                usuario=usuario_atual["email"],
                detalhes={"total_candidatos": len(candidatos)},
            )
            return {
                "sucesso": True,
                "match": candidatos[0],
                "matches": candidatos,
            }

        registrar_evento(
            endpoint="/dar_match",
            acao="calcular_match",
            status="sem_match",
            mensagem="Nenhum match encontrado.",
            usuario=usuario_atual["email"],
        )
        return {"sucesso": False, "mensagem": "Nenhum match encontrado."}
    except Exception as erro:
        registrar_evento(
            endpoint="/dar_match",
            acao="calcular_match",
            status="erro",
            mensagem="Falha ao calcular match.",
            usuario=usuario_atual["email"],
            detalhes={"erro": str(erro)},
        )
        raise HTTPException(status_code=503, detail="Falha interna ao calcular match.") from erro

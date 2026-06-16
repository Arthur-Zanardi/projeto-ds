"""Camada de dados relacional sobre PostgreSQL (SQLAlchemy).

Reimplementa as funções públicas antes expostas por `sqlite_db.py`,
mantendo as mesmas assinaturas e formatos de retorno. O esquema é criado
apenas via Alembic — nada de CREATE TABLE em runtime.
"""
import hashlib
import logging

import bcrypt
from sqlalchemy import func, select, union
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db_models import (
    AcaoMatch,
    ConversaMatch,
    HistoricoChat,
    LogApi,
    MatchUsuario,
    MensagemConversa,
    PerfilPublico,
    Usuario,
    VetorSalvo,
)
from src.services.db import session_scope
from src.services.interfaces import IUserRepository
from src.services.profile_completion import FOTO_PADRAO
from src.services.user_context import normalizar_email_usuario, normalizar_nome_usuario

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _normalizar_identificador(valor: str | None) -> str:
    return str(valor or "").strip().lower()


def _fmt_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt is not None else None


def _gerar_conversa_id(participante_a: str, participante_b: str) -> str:
    primeiro, segundo = sorted(
        [_normalizar_identificador(participante_a), _normalizar_identificador(participante_b)]
    )
    digest = hashlib.sha1(f"{primeiro}|{segundo}".encode("utf-8")).hexdigest()[:16]
    return f"conv_{digest}"


def _formatar_match(m: MatchUsuario | None):
    if m is None:
        return None
    return {
        "id": m.id,
        "usuario": m.usuario,
        "match_id": m.match_id,
        "nome": m.nome,
        "afinidade": m.afinidade,
        "dados_match": m.dados_match,
        "data_hora": _fmt_dt(m.data_hora),
        "conversa_id": m.conversa_id,
    }


def _formatar_perfil_publico(p: PerfilPublico | None):
    if p is None:
        return None
    return {
        "id": p.usuario,
        "match_id": p.usuario,
        "usuario": p.usuario,
        "nome": p.nome,
        "idade": p.idade,
        "imagem": p.foto_url or FOTO_PADRAO,
        "foto_url": p.foto_url or FOTO_PADRAO,
        "descricao": p.descricao or "",
        "localizacao": p.localizacao or "",
        "cargo": p.cargo or "",
        "origem": p.origem,
        "mock_customizado": bool(p.mock_customizado),
        "data_hora": _fmt_dt(p.data_hora),
    }


# --------------------------------------------------------------------------
# Chat / histórico
# --------------------------------------------------------------------------
def salvar_mensagem(usuario: str, remetente: str, mensagem: str):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        s.add(HistoricoChat(usuario=usuario, remetente=remetente, mensagem=mensagem))
    logger.info("Mensagem salva: %s | %s | %s", usuario, remetente, mensagem[:50])


def obter_historico_chat(usuario: str):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        linhas = s.execute(
            select(HistoricoChat.remetente, HistoricoChat.mensagem)
            .where(HistoricoChat.usuario == usuario)
            .order_by(HistoricoChat.id.asc())
        ).all()
    return [{"remetente": r.remetente, "mensagem": r.mensagem} for r in linhas]


# --------------------------------------------------------------------------
# Matches
# --------------------------------------------------------------------------
def _garantir_conversa(s, conversa_id: str, participante_1: str, participante_2: str, tipo: str):
    stmt = (
        pg_insert(ConversaMatch)
        .values(
            conversa_id=conversa_id,
            participante_1=participante_1,
            participante_2=participante_2,
            tipo=tipo,
        )
        .on_conflict_do_nothing(index_elements=["conversa_id"])
    )
    s.execute(stmt)


def criar_match_usuario(
    usuario: str,
    match_id: str,
    nome: str,
    afinidade: str | None = None,
    dados_match: dict | None = None,
    conversa_id: str | None = None,
    tipo: str = "mock",
):
    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    conversa_id = conversa_id or _gerar_conversa_id(usuario, match_id)

    with session_scope() as s:
        _garantir_conversa(s, conversa_id, usuario, match_id, tipo)
        stmt = (
            pg_insert(MatchUsuario)
            .values(
                usuario=usuario,
                match_id=match_id,
                nome=nome,
                afinidade=afinidade,
                dados_match=dados_match,
                conversa_id=conversa_id,
            )
            .on_conflict_do_update(
                index_elements=["usuario", "match_id"],
                set_={
                    "nome": nome,
                    "afinidade": afinidade,
                    "dados_match": dados_match,
                    "conversa_id": conversa_id,
                    "data_hora": func.now(),
                },
            )
        )
        s.execute(stmt)
        match = s.execute(
            select(MatchUsuario).where(
                MatchUsuario.usuario == usuario, MatchUsuario.match_id == match_id
            )
        ).scalar_one()
        resultado = _formatar_match(match)
    logger.info("Match salvo: %s | %s", usuario, match_id)
    return resultado


def confirmar_match(
    usuario: str,
    candidato_id: str,
    perfil_candidato: dict,
    perfil_usuario: dict | None = None,
    tipo: str = "real",
    sugestoes: list[dict] | None = None,
):
    usuario = normalizar_email_usuario(usuario)
    candidato_id = _normalizar_identificador(candidato_id)
    conversa_id = _gerar_conversa_id(usuario, candidato_id)
    sugestoes = sugestoes or []

    dados_candidato = dict(perfil_candidato or {})
    dados_candidato.update(
        {
            "id": candidato_id,
            "match_id": candidato_id,
            "tipo": tipo,
            "match_confirmado": True,
            "sugestoes_inicio": sugestoes,
        }
    )
    match_usuario = criar_match_usuario(
        usuario=usuario,
        match_id=candidato_id,
        nome=dados_candidato.get("nome") or normalizar_nome_usuario(None, candidato_id),
        afinidade=dados_candidato.get("afinidade"),
        dados_match=dados_candidato,
        conversa_id=conversa_id,
        tipo=tipo,
    )

    if tipo == "real":
        perfil_usuario = dict(perfil_usuario or obter_perfil_publico(usuario) or {})
        perfil_usuario.update(
            {
                "id": usuario,
                "match_id": usuario,
                "tipo": tipo,
                "match_confirmado": True,
                "sugestoes_inicio": sugestoes,
            }
        )
        criar_match_usuario(
            usuario=candidato_id,
            match_id=usuario,
            nome=perfil_usuario.get("nome") or normalizar_nome_usuario(None, usuario),
            afinidade=perfil_usuario.get("afinidade"),
            dados_match=perfil_usuario,
            conversa_id=conversa_id,
            tipo=tipo,
        )

    return match_usuario


def obter_match_usuario(usuario: str, match_id: str):
    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    with session_scope() as s:
        match = s.execute(
            select(MatchUsuario).where(
                MatchUsuario.usuario == usuario, MatchUsuario.match_id == match_id
            )
        ).scalar_one_or_none()
        return _formatar_match(match)


def listar_matches_usuario(usuario: str):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        matches = (
            s.execute(
                select(MatchUsuario)
                .where(MatchUsuario.usuario == usuario)
                .order_by(MatchUsuario.id.asc())
            )
            .scalars()
            .all()
        )
        return [_formatar_match(m) for m in matches]


def salvar_mensagem_match(usuario: str, match_id: str, remetente: str, mensagem: str):
    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)

    with session_scope() as s:
        match = s.execute(
            select(MatchUsuario).where(
                MatchUsuario.usuario == usuario, MatchUsuario.match_id == match_id
            )
        ).scalar_one_or_none()
        if match is None:
            raise ValueError("Match nao encontrado.")

        remetente_normalizado = remetente
        if remetente == "usuario":
            remetente_normalizado = usuario
        elif remetente == "match":
            remetente_normalizado = match_id

        s.add(
            MensagemConversa(
                conversa_id=match.conversa_id,
                remetente=remetente_normalizado,
                mensagem=mensagem,
            )
        )
    logger.info("Mensagem de match salva: %s | %s | %s", usuario, match_id, remetente)


def obter_historico_match(usuario: str, match_id: str):
    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    with session_scope() as s:
        match = s.execute(
            select(MatchUsuario).where(
                MatchUsuario.usuario == usuario, MatchUsuario.match_id == match_id
            )
        ).scalar_one_or_none()
        if match is None:
            return []
        linhas = s.execute(
            select(MensagemConversa.remetente, MensagemConversa.mensagem)
            .where(MensagemConversa.conversa_id == match.conversa_id)
            .order_by(MensagemConversa.id.asc())
        ).all()
    return [
        {
            "remetente": "usuario" if r.remetente == usuario else "match",
            "mensagem": r.mensagem,
        }
        for r in linhas
    ]


# --------------------------------------------------------------------------
# Vetores (armazenamento JSON do último vetor calculado)
# --------------------------------------------------------------------------
def salvar_vetores_sqlite(usuario: str, vetores_dict: dict):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        s.add(VetorSalvo(usuario=usuario, vetores_json=vetores_dict))
    logger.info("Vetores salvos para usuario: %s", usuario)


def obter_ultimo_vetor_sqlite(usuario: str):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        vetor = s.execute(
            select(VetorSalvo.vetores_json)
            .where(VetorSalvo.usuario == usuario)
            .order_by(VetorSalvo.id.desc())
            .limit(1)
        ).scalar_one_or_none()
    return vetor


# --------------------------------------------------------------------------
# Perfis públicos
# --------------------------------------------------------------------------
def salvar_perfil_publico(
    usuario: str,
    nome: str,
    idade: int | str | None = None,
    foto_url: str | None = None,
    descricao: str | None = None,
    localizacao: str | None = None,
    cargo: str | None = None,
    origem: str = "real",
    mock_customizado: bool = False,
):
    usuario = _normalizar_identificador(usuario)
    if not usuario:
        raise ValueError("Usuario do perfil publico nao pode ser vazio.")

    try:
        idade_normalizada = int(idade) if idade not in (None, "") else None
    except (TypeError, ValueError):
        idade_normalizada = None

    nome_normalizado = (nome or "").strip() or normalizar_nome_usuario(None, usuario)
    foto_url = (foto_url or FOTO_PADRAO).strip()
    descricao = (descricao or "Perfil em construcao.").strip()
    localizacao = (localizacao or "Localizacao nao informada").strip()
    cargo = (cargo or "Explorando novas conexoes").strip()
    origem = (origem or "real").strip().lower()

    with session_scope() as s:
        stmt = (
            pg_insert(PerfilPublico)
            .values(
                usuario=usuario,
                nome=nome_normalizado,
                idade=idade_normalizada,
                foto_url=foto_url,
                descricao=descricao,
                localizacao=localizacao,
                cargo=cargo,
                origem=origem,
                mock_customizado=bool(mock_customizado),
            )
            .on_conflict_do_update(
                index_elements=["usuario"],
                set_={
                    "nome": nome_normalizado,
                    "idade": idade_normalizada,
                    "foto_url": foto_url,
                    "descricao": descricao,
                    "localizacao": localizacao,
                    "cargo": cargo,
                    "origem": origem,
                    "mock_customizado": bool(mock_customizado),
                    "data_hora": func.now(),
                },
            )
        )
        s.execute(stmt)
        perfil = s.execute(
            select(PerfilPublico).where(PerfilPublico.usuario == usuario)
        ).scalar_one()
        return _formatar_perfil_publico(perfil)


def obter_perfil_publico(usuario: str):
    usuario = _normalizar_identificador(usuario)
    with session_scope() as s:
        perfil = s.execute(
            select(PerfilPublico).where(PerfilPublico.usuario == usuario)
        ).scalar_one_or_none()
        return _formatar_perfil_publico(perfil)


def listar_perfis_publicos():
    with session_scope() as s:
        perfis = (
            s.execute(select(PerfilPublico).order_by(PerfilPublico.nome.asc()))
            .scalars()
            .all()
        )
        return [_formatar_perfil_publico(p) for p in perfis]


# --------------------------------------------------------------------------
# Ações de match (like / pass)
# --------------------------------------------------------------------------
def registrar_acao_match(usuario: str, candidato_id: str, acao: str):
    usuario = normalizar_email_usuario(usuario)
    candidato_id = _normalizar_identificador(candidato_id)
    acao = (acao or "").strip().lower()
    if acao not in {"like", "pass"}:
        raise ValueError("Acao de match invalida.")

    with session_scope() as s:
        stmt = (
            pg_insert(AcaoMatch)
            .values(usuario=usuario, candidato_id=candidato_id, acao=acao)
            .on_conflict_do_update(
                index_elements=["usuario", "candidato_id"],
                set_={"acao": acao, "data_hora": func.now()},
            )
        )
        s.execute(stmt)
    return obter_acao_match(usuario, candidato_id)


def obter_acao_match(usuario: str, candidato_id: str):
    usuario = normalizar_email_usuario(usuario)
    candidato_id = _normalizar_identificador(candidato_id)
    with session_scope() as s:
        acao = s.execute(
            select(AcaoMatch).where(
                AcaoMatch.usuario == usuario, AcaoMatch.candidato_id == candidato_id
            )
        ).scalar_one_or_none()
        if acao is None:
            return None
        return {
            "usuario": acao.usuario,
            "candidato_id": acao.candidato_id,
            "acao": acao.acao,
            "data_hora": _fmt_dt(acao.data_hora),
        }


def listar_ids_indisponiveis_match(usuario: str):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        consulta = union(
            select(AcaoMatch.candidato_id.label("id")).where(AcaoMatch.usuario == usuario),
            select(MatchUsuario.match_id.label("id")).where(MatchUsuario.usuario == usuario),
        )
        ids = {linha[0] for linha in s.execute(consulta).all()}
    return ids


# --------------------------------------------------------------------------
# Logs da API
# --------------------------------------------------------------------------
def registrar_log_api(
    usuario: str,
    endpoint: str,
    acao: str,
    status: str,
    mensagem: str,
    detalhes: dict | None = None,
):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        s.add(
            LogApi(
                usuario=usuario,
                endpoint=endpoint,
                acao=acao,
                status=status,
                mensagem=mensagem,
                detalhes_json=detalhes,
            )
        )
    logger.info("Log API: %s | %s | %s | %s", usuario, endpoint, acao, status)


def obter_logs_api(usuario: str):
    usuario = normalizar_email_usuario(usuario)
    with session_scope() as s:
        linhas = (
            s.execute(
                select(LogApi).where(LogApi.usuario == usuario).order_by(LogApi.id.asc())
            )
            .scalars()
            .all()
        )
    return [
        {
            "endpoint": log.endpoint,
            "acao": log.acao,
            "status": log.status,
            "mensagem": log.mensagem,
            "detalhes": log.detalhes_json,
            "data_hora": _fmt_dt(log.data_hora),
        }
        for log in linhas
    ]


# --------------------------------------------------------------------------
# Repositório de usuários (autenticação)
# --------------------------------------------------------------------------
class PostgresUserRepository(IUserRepository):
    def criar_usuario(
        self,
        email: str,
        senha_pura: str,
        nome: str | None = None,
        idade: int | str | None = None,
        foto_url: str | None = None,
        descricao: str | None = None,
        localizacao: str | None = None,
        cargo: str | None = None,
    ) -> bool:
        email = _normalizar_identificador(email)
        nome = normalizar_nome_usuario(nome, email)

        if not email or not senha_pura:
            return False

        senha_hash = bcrypt.hashpw(senha_pura.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        with session_scope() as s:
            existe = s.execute(
                select(Usuario.id).where(Usuario.email == email)
            ).scalar_one_or_none()
            if existe is not None:
                return False
            s.add(Usuario(nome=nome, email=email, senha_hash=senha_hash))

        salvar_perfil_publico(
            usuario=email,
            nome=nome,
            idade=idade,
            foto_url=foto_url,
            descricao=descricao,
            localizacao=localizacao,
            cargo=cargo,
            origem="real",
            mock_customizado=False,
        )
        return True

    def buscar_usuario_por_email(self, email: str) -> dict | None:
        email = _normalizar_identificador(email)
        if not email:
            return None
        with session_scope() as s:
            usuario = s.execute(
                select(Usuario).where(Usuario.email == email)
            ).scalar_one_or_none()
            if usuario is None:
                return None
            return {
                "id": usuario.id,
                "nome": usuario.nome,
                "email": usuario.email,
                "senha_hash": usuario.senha_hash,
            }

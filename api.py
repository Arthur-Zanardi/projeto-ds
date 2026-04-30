from __future__ import annotations

import secrets
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src.schema.schema_vetores import (
    DEFAULT_VISIBLE_FIELDS,
    flatten_query_vectors,
    merge_extracted_profile,
    merge_interests_override,
    normalize_profile_vectors,
    top_interests_summary,
)
from src.services import postgres_db as db
from src.services.auth_service import (
    build_google_authorization_url,
    create_access_token,
    decode_access_token,
    exchange_google_code,
    google_oauth_configured,
    hash_password,
    verify_password,
)
from src.services.database import (
    buscar_melhor_match,
    obter_perfil_vetorial,
    popular_banco_mock,
    salvar_perfil_usuario,
)
from src.services.llm_service import extrair_vetores_da_conversa, gerar_resposta_ia
from src.services.match_service import (
    compatibility_breakdown,
    explain_match,
    generate_icebreaker,
    passes_value_filters,
    public_match_profile,
)


app = FastAPI(
    title="MatchAI API",
    description="Backend para o aplicativo de relacionamento com IA e matching vetorial.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


class AuthRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class MensagemUsuario(BaseModel):
    texto: str | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    theme_mode: str | None = Field(default=None, pattern="^(light|dark)$")
    chat_font_scale: float | None = Field(default=None, ge=0.8, le=1.6)
    ui_font_scale: float | None = Field(default=None, ge=0.8, le=1.8)
    accessibility_mode: bool | None = None


class InterestsUpdate(BaseModel):
    interests: dict[str, float]


class PhysicalUpdate(BaseModel):
    fisico: dict[str, float]


class PhotoUpdate(BaseModel):
    photo_path: str


class VisibilityUpdate(BaseModel):
    visible_fields: dict[str, bool]


class ValueFilterItem(BaseModel):
    key: str
    active: bool = True
    min_value: float | None = Field(default=None, ge=0.0, le=1.0)
    max_value: float | None = Field(default=None, ge=0.0, le=1.0)
    max_delta: float | None = Field(default=None, ge=0.0, le=1.0)


class ValueFiltersUpdate(BaseModel):
    filters: list[ValueFilterItem]


class MatchMessageCreate(BaseModel):
    mensagem: str


@app.on_event("startup")
def startup() -> None:
    db.init_database()
    popular_banco_mock()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Autenticacao obrigatoria.")

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = db.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    return user


def _auth_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "token": create_access_token(user),
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
        },
    }


def _history_text(user_id: str) -> str:
    messages = db.list_profile_chat_messages(user_id)
    return "\n".join(
        item["mensagem"] for item in messages if item.get("remetente") == "usuario"
    )


def _save_dynamic_profile(
    user: dict[str, Any],
    source_text: str | None,
) -> dict[str, Any]:
    text_to_analyze = (source_text or "").strip() or _history_text(user["id"])
    extracted_profile = extrair_vetores_da_conversa(text_to_analyze)
    current_profile = db.get_profile(user["id"])
    profile_json = merge_extracted_profile(current_profile.get("vector_json"), extracted_profile)
    saved_profile = db.save_profile_vectors(user["id"], profile_json)
    vector_profile = merge_interests_override(
        saved_profile["profile_json"],
        saved_profile.get("interests_override"),
    )
    salvar_perfil_usuario(
        user["id"],
        saved_profile.get("display_name") or user["display_name"],
        vector_profile,
        bio=saved_profile.get("bio", ""),
    )
    return saved_profile


def _candidate_profile(candidate_id: str) -> dict[str, Any] | None:
    user = db.get_user_by_id(candidate_id)
    if user:
        profile = db.get_profile(candidate_id)
        return {
            "id": candidate_id,
            "nome": profile.get("display_name") or user["display_name"],
            "bio": profile.get("bio", ""),
            "photo_path": profile.get("photo_path", ""),
            "profile_json": profile.get("vector_json") or profile.get("profile_json"),
            "visible_fields": profile.get("visible_fields", DEFAULT_VISIBLE_FIELDS),
        }
    return obter_perfil_vetorial(candidate_id)


def _sync_profile_to_vector_store(user: dict[str, Any], profile: dict[str, Any]) -> None:
    salvar_perfil_usuario(
        user["id"],
        profile.get("display_name") or user["display_name"],
        profile.get("vector_json") or profile.get("profile_json"),
        bio=profile.get("bio", ""),
    )


@app.get("/")
def read_root():
    return {"mensagem": "API do MatchAI esta pronta."}


@app.post("/auth/register")
def register(payload: AuthRequest):
    email = payload.email.lower().strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail invalido.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres.")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="E-mail ja cadastrado.")

    user = db.create_user(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or email.split("@", 1)[0],
    )
    return _auth_payload(user)


@app.post("/auth/login")
def login(payload: AuthRequest):
    user = db.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="E-mail ou senha invalidos.")
    return _auth_payload(user)


@app.get("/auth/google/start")
def google_start():
    if not google_oauth_configured():
        return {
            "enabled": False,
            "mensagem": "Google OAuth nao configurado no .env.",
        }

    state = secrets.token_urlsafe(24)
    db.create_oauth_session(state)
    return {
        "enabled": True,
        "state": state,
        "auth_url": build_google_authorization_url(state),
    }


@app.get("/auth/google/callback", response_class=HTMLResponse)
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if not state:
        return "<h1>MatchAI</h1><p>Estado OAuth ausente.</p>"
    if error:
        db.fail_oauth_session(state, error)
        return "<h1>MatchAI</h1><p>Login cancelado. Voce pode fechar esta janela.</p>"

    try:
        if not code:
            raise RuntimeError("Codigo OAuth ausente.")
        google_user = exchange_google_code(code)
        user = db.upsert_google_user(
            email=google_user["email"],
            display_name=google_user["display_name"],
        )
        token = create_access_token(user)
        db.complete_oauth_session(
            state,
            token=token,
            email=user["email"],
            display_name=user["display_name"],
        )
    except Exception as exc:
        db.fail_oauth_session(state, str(exc))
        return f"<h1>MatchAI</h1><p>Erro no login: {exc}</p>"

    return "<h1>MatchAI</h1><p>Login concluido. Voce pode voltar ao app.</p>"


@app.get("/auth/google/status/{state}")
def google_status(state: str):
    session = db.get_oauth_session(state)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao OAuth nao encontrada.")
    if session.get("error"):
        return {"status": "error", "error": session["error"]}
    if session.get("token"):
        return {
            "status": "done",
            "token": session["token"],
            "user": {
                "email": session["email"],
                "display_name": session["display_name"],
            },
        }
    return {"status": "pending"}


@app.get("/me")
def me(user: dict[str, Any] = Depends(current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "profile": db.get_profile(user["id"]),
    }


@app.get("/historico")
def pegar_historico(user: dict[str, Any] = Depends(current_user)):
    return {"historico": db.list_profile_chat_messages(user["id"])}


@app.post("/chat")
def conversar_com_ia(
    mensagem: MensagemUsuario,
    user: dict[str, Any] = Depends(current_user),
):
    texto = (mensagem.texto or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")

    db.save_profile_chat_message(user["id"], "usuario", texto)
    historico = db.list_profile_chat_messages(user["id"])
    resposta = gerar_resposta_ia(texto, historico=historico)
    db.save_profile_chat_message(user["id"], "ia", resposta)
    return {"resposta": resposta}


@app.post("/analisar_perfil")
def analisar_perfil(
    mensagem: MensagemUsuario,
    user: dict[str, Any] = Depends(current_user),
):
    profile = _save_dynamic_profile(user, mensagem.texto)
    return {
        "texto_analisado": (mensagem.texto or "").strip() or _history_text(user["id"]),
        "vetores_calculados": profile["vector_json"],
        "profile": profile,
    }


@app.get("/profile")
def get_profile(user: dict[str, Any] = Depends(current_user)):
    return db.get_profile(user["id"])


@app.patch("/profile")
def update_profile(
    payload: ProfileUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if "display_name" in updates and updates["display_name"]:
        updates["display_name"] = updates["display_name"].strip()
    if "bio" in updates and updates["bio"] is not None:
        updates["bio"] = updates["bio"].strip()

    profile = db.update_profile(user["id"], updates)
    _sync_profile_to_vector_store(user, profile)
    return profile


@app.patch("/profile/interests")
def update_interests(
    payload: InterestsUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    profile = db.get_profile(user["id"])
    merged = merge_interests_override(profile["profile_json"], payload.interests)
    db.update_profile(user["id"], {"interests_override": payload.interests})
    saved = db.save_profile_vectors(user["id"], merged)
    _sync_profile_to_vector_store(user, saved)
    return saved


@app.patch("/profile/physical")
def update_physical_profile(
    payload: PhysicalUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    saved = db.save_physical_profile(user["id"], payload.fisico)
    _sync_profile_to_vector_store(user, saved)
    return saved


@app.patch("/profile/photo")
def update_profile_photo(
    payload: PhotoUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    photo_path = payload.photo_path.strip()
    profile = db.update_profile_photo(user["id"], photo_path)
    return profile


@app.get("/profile/readiness")
def get_profile_readiness(user: dict[str, Any] = Depends(current_user)):
    return db.get_profile_readiness(user["id"])


@app.patch("/profile/visibility")
def update_visibility(
    payload: VisibilityUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    visible_fields = {**DEFAULT_VISIBLE_FIELDS, **payload.visible_fields}
    return db.update_profile(user["id"], {"visible_fields": visible_fields})


@app.patch("/profile/value-filters")
def update_value_filters(
    payload: ValueFiltersUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    return {"filters": db.upsert_value_filters(user["id"], [item.model_dump() for item in payload.filters])}


@app.get("/profile/value-filters")
def get_value_filters(user: dict[str, Any] = Depends(current_user)):
    return {"filters": db.list_value_filters(user["id"])}


@app.get("/profile/export")
def export_profile(user: dict[str, Any] = Depends(current_user)):
    return db.export_user_data(user["id"])


@app.delete("/profile")
def delete_profile_data(user: dict[str, Any] = Depends(current_user)):
    return db.delete_profile_data(user["id"])


@app.post("/dar_match")
def calcular_match_final(
    mensagem: MensagemUsuario,
    user: dict[str, Any] = Depends(current_user),
):
    readiness = db.get_profile_readiness(user["id"])
    if not readiness["ready"]:
        missing_labels = {
            "questionario_fisico": "preencher o questionario fisico",
            "conversa_ia": "conversar um pouco mais com a IA",
        }
        faltando = ", ".join(missing_labels.get(item, item) for item in readiness["missing"])
        return {
            "sucesso": False,
            "mensagem": f"Antes do match, falta {faltando}.",
            "readiness": readiness,
        }

    profile = _save_dynamic_profile(user, mensagem.texto)
    user_vector_profile = profile.get("vector_json") or profile.get("profile_json")
    vetor_calculado = flatten_query_vectors(user_vector_profile)
    raw_candidates = buscar_melhor_match(user["id"], vetor_calculado, quantidade=20)
    filtros = db.list_value_filters(user["id"])
    approved: list[dict[str, Any]] = []

    for candidate in raw_candidates:
        candidate_profile = normalize_profile_vectors(candidate.get("profile_json"))
        ok, _reason = passes_value_filters(user_vector_profile, candidate_profile, filtros)
        if not ok:
            continue

        breakdown = compatibility_breakdown(user_vector_profile, candidate_profile)
        explanation = explain_match(user_vector_profile, candidate_profile, candidate["nome"])
        approved.append(
            {
                **candidate,
                "afinidade_numero": breakdown["overall_affinity"],
                "afinidade": f"{breakdown['overall_affinity']}%",
                "distancia_chroma": candidate["distancia_matematica"],
                "distancia_matematica": round(1 - (breakdown["overall_affinity"] / 100), 4),
                "explanation": explanation,
                "compatibility_breakdown": breakdown,
                "top_interests_summary": breakdown["top_interests"],
            }
        )

    approved = sorted(approved, key=lambda item: item["afinidade_numero"], reverse=True)[:5]

    saved_matches: list[dict[str, Any]] = []
    for candidate in approved:
        match_row = db.create_or_update_match(
            user_id=user["id"],
            matched_user_id=candidate["id"],
            matched_name=candidate["nome"],
            affinity=candidate["afinidade_numero"],
            distance=candidate["distancia_matematica"],
            explanation=candidate["explanation"],
        )
        saved_matches.append(
            {
                **candidate,
                "match_id": match_row["id"],
            }
        )

    if saved_matches:
        return {"sucesso": True, "match": saved_matches[0], "matches": saved_matches}
    return {
        "sucesso": False,
        "mensagem": "Nenhum match encontrado depois dos filtros de valores.",
    }


@app.get("/matches")
def get_matches(user: dict[str, Any] = Depends(current_user)):
    return {"matches": db.list_matches(user["id"])}


@app.get("/matches/{match_id}/profile")
def get_match_profile(
    match_id: str,
    user: dict[str, Any] = Depends(current_user),
):
    match_row = db.get_match(match_id, user["id"])
    if not match_row:
        raise HTTPException(status_code=404, detail="Match nao encontrado.")

    candidate = _candidate_profile(match_row["matched_user_id"])
    if not candidate:
        raise HTTPException(status_code=404, detail="Perfil do match nao encontrado.")

    public_profile = public_match_profile(
        candidate.get("profile_json", {}),
        candidate.get("visible_fields", DEFAULT_VISIBLE_FIELDS),
    )
    user_profile = db.get_profile(user["id"])
    breakdown = compatibility_breakdown(
        user_profile.get("vector_json") or user_profile.get("profile_json"),
        candidate.get("profile_json", {}),
    )
    return {
        "match": match_row,
        "profile": {
            "id": candidate["id"],
            "nome": candidate["nome"],
            "bio": candidate.get("bio", ""),
            "photo_path": candidate.get("photo_path", ""),
            "top_interests_summary": top_interests_summary(candidate.get("profile_json", {})),
            "compatibility_breakdown": breakdown,
            "public_profile": public_profile,
        },
    }


@app.post("/matches/{match_id}/icebreaker")
def get_icebreaker(
    match_id: str,
    user: dict[str, Any] = Depends(current_user),
):
    match_row = db.get_match(match_id, user["id"])
    if not match_row:
        raise HTTPException(status_code=404, detail="Match nao encontrado.")

    user_profile = db.get_profile(user["id"])
    candidate = _candidate_profile(match_row["matched_user_id"])
    if not candidate:
        raise HTTPException(status_code=404, detail="Perfil do match nao encontrado.")

    sugestao = generate_icebreaker(
        user_profile.get("vector_json") or user_profile.get("profile_json"),
        candidate.get("profile_json", {}),
        candidate["nome"],
    )
    return {"sugestao": sugestao}


@app.get("/matches/{match_id}/messages")
def get_match_messages(
    match_id: str,
    user: dict[str, Any] = Depends(current_user),
):
    match_row = db.get_match(match_id, user["id"])
    if not match_row:
        raise HTTPException(status_code=404, detail="Match nao encontrado.")
    return {"messages": db.list_match_messages(match_id)}


@app.post("/matches/{match_id}/messages")
def post_match_message(
    match_id: str,
    payload: MatchMessageCreate,
    user: dict[str, Any] = Depends(current_user),
):
    match_row = db.get_match(match_id, user["id"])
    if not match_row:
        raise HTTPException(status_code=404, detail="Match nao encontrado.")
    mensagem = payload.mensagem.strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    return {"message": db.save_match_message(match_id, user["id"], mensagem)}

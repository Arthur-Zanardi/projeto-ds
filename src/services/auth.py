"""Autenticação JWT do MatchAI.

Gera e valida tokens assinados com `JWT_SECRET`. A dependency
`get_current_user` extrai a identidade do header `Authorization: Bearer`.
Sem token válido, os endpoints protegidos respondem 401.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import settings
from src.services.user_context import usuario_eh_admin

bearer_scheme = HTTPBearer(auto_error=False)

_NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Nao autenticado.",
    headers={"WWW-Authenticate": "Bearer"},
)


def criar_access_token(
    email: str,
    nome: str,
    is_admin: bool,
    expires_minutes: int | None = None,
) -> str:
    minutos = expires_minutes or settings.access_token_expire_minutes
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": email.strip().lower(),
        "nome": nome,
        "is_admin": bool(is_admin),
        "iat": agora,
        "exp": agora + timedelta(minutes=minutos),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def get_current_user(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credenciais is None or not credenciais.credentials:
        raise _NAO_AUTENTICADO
    try:
        payload = decodificar_token(credenciais.credentials)
    except JWTError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from erro

    email = str(payload.get("sub") or "").strip().lower()
    if not email:
        raise _NAO_AUTENTICADO

    nome = payload.get("nome") or email.split("@")[0]
    is_admin = bool(payload.get("is_admin")) or usuario_eh_admin(email)
    return {"email": email, "nome": nome, "is_admin": is_admin}


async def require_admin(usuario: dict = Depends(get_current_user)) -> dict:
    if not usuario.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta acao.",
        )
    return usuario

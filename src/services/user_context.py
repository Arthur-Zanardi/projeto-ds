"""Identidade do usuário e helpers de normalização.

Nenhum dado pessoal é fixado no código. Administradores vêm de
`settings.admin_emails_set` (variável ADMIN_EMAILS). Em produção a
identidade real vem do JWT (ver `get_current_user` na API).
"""
import os

from src.config import settings

# Administradores centralizados em settings (ADMIN_EMAILS="a@x.com,b@y.com")
ADMIN_EMAILS = settings.admin_emails_set

# Padrões legados (sem dados pessoais). Vazios por padrão; mantidos apenas
# para compatibilidade com a camada de dados legada até a migração concluir.
EMAIL_USUARIO_PADRAO = os.getenv("EMAIL_USUARIO_PADRAO", "").strip().lower()
NOME_USUARIO_PADRAO = os.getenv("NOME_USUARIO_PADRAO", "").strip()
USUARIO_LEGADO = os.getenv("USUARIO_LEGADO", "").strip().lower()


def normalizar_email_usuario(email: str | None) -> str:
    """Normaliza um e-mail. Sem e-mail e sem padrão configurado, retorna "".

    O comportamento antigo de devolver um e-mail de admin por padrão foi
    removido por ser fonte de impersonação. A identidade real vem do JWT.
    """
    email_normalizado = (email or "").strip().lower()
    return email_normalizado or EMAIL_USUARIO_PADRAO


def normalizar_nome_usuario(nome: str | None, email: str | None = None) -> str:
    nome_normalizado = (nome or "").strip()

    if nome_normalizado:
        return nome_normalizado

    email_normalizado = normalizar_email_usuario(email)

    if not email_normalizado:
        return NOME_USUARIO_PADRAO or "Usuario"

    if EMAIL_USUARIO_PADRAO and email_normalizado == EMAIL_USUARIO_PADRAO and NOME_USUARIO_PADRAO:
        return NOME_USUARIO_PADRAO

    return email_normalizado.split("@")[0].replace(".", " ").title()


def usuario_eh_admin(email: str | None) -> bool:
    email_normalizado = normalizar_email_usuario(email)
    return bool(email_normalizado) and email_normalizado in ADMIN_EMAILS

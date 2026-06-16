ADMIN_EMAILS = {"rafaellapipucos@gmail.com"}
EMAIL_USUARIO_PADRAO = "rafaellapipucos@gmail.com"
NOME_USUARIO_PADRAO = "Rafaell"
USUARIO_LEGADO = "user_rafaell"


def normalizar_email_usuario(email: str | None) -> str:
    email_normalizado = (email or "").strip().lower()
    return email_normalizado or EMAIL_USUARIO_PADRAO


def normalizar_nome_usuario(nome: str | None, email: str | None = None) -> str:
    nome_normalizado = (nome or "").strip()

    if nome_normalizado:
        return nome_normalizado

    email_normalizado = normalizar_email_usuario(email)

    if email_normalizado == EMAIL_USUARIO_PADRAO:
        return NOME_USUARIO_PADRAO

    return email_normalizado.split("@")[0].replace(".", " ").title()


def usuario_eh_admin(email: str | None) -> bool:
    return normalizar_email_usuario(email) in ADMIN_EMAILS

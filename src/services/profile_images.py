import re
import uuid


MAX_PROFILE_IMAGE_BYTES = 16 * 1024 * 1024
ALLOWED_PROFILE_IMAGE_EXTENSIONS = ("jpeg", "jpg", "png", "webp")


def extensao_imagem(nome_arquivo: str | None) -> str:
    nome = str(nome_arquivo or "").strip().lower()
    if "." not in nome:
        return ""
    return nome.rsplit(".", 1)[-1]


def validar_imagem_perfil(
    nome_arquivo: str | None,
    tamanho_bytes: int | None,
) -> tuple[bool, str]:
    extensao = extensao_imagem(nome_arquivo)
    tamanho = int(tamanho_bytes or 0)

    if extensao not in ALLOWED_PROFILE_IMAGE_EXTENSIONS:
        permitidas = ", ".join(ALLOWED_PROFILE_IMAGE_EXTENSIONS)
        return False, f"Selecione uma imagem {permitidas}."

    if tamanho > MAX_PROFILE_IMAGE_BYTES:
        return False, "A imagem deve ter no maximo 16 MB."

    return True, ""


def email_para_pasta(email: str | None) -> str:
    seguro = re.sub(r"[^a-z0-9]+", "_", str(email or "").strip().lower()).strip("_")
    return seguro or "usuario"


def gerar_caminho_upload_imagem(
    email: str | None,
    nome_arquivo: str | None,
    token: str | None = None,
) -> str:
    extensao = extensao_imagem(nome_arquivo) or "jpg"
    identificador = token or uuid.uuid4().hex
    return f"uploads/profile_images/{email_para_pasta(email)}/{identificador}.{extensao}"

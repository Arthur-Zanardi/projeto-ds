from src.views.tela_perfil import profileView
from src.services.profile_completion import campos_faltantes_perfil, perfil_publico_completo
from src.services.profile_images import (
    MAX_PROFILE_IMAGE_BYTES,
    gerar_caminho_upload_imagem,
    validar_imagem_perfil,
)


class PageFake:
    def __init__(self):
        self.usuario_logado = {"email": "fellipe@example.com", "nome": "Fellipe"}

    def run_task(self, *args, **kwargs):
        return None

    def update(self):
        return None

    def go(self, route):
        self.route = route


def coletar_textos(control):
    textos = []

    if isinstance(control, str):
        return [control]

    value = getattr(control, "value", None)
    if isinstance(value, str):
        textos.append(value)

    for attr in ("label", "hint_text", "tooltip"):
        value = getattr(control, attr, None)
        if isinstance(value, str):
            textos.append(value)

    content = getattr(control, "content", None)
    if isinstance(content, str):
        textos.append(content)
    elif content is not None:
        textos.extend(coletar_textos(content))

    for child in getattr(control, "controls", []) or []:
        textos.extend(coletar_textos(child))

    return textos


def test_profile_view_nao_renderiza_tags_de_personalidade():
    view = profileView(PageFake())
    texto = " ".join(coletar_textos(view))

    assert "Tags de personalidade" not in texto
    assert "Alma Criativa" not in texto


def test_profile_view_tem_perguntas_dedicadas_upload_e_sem_url():
    view = profileView(PageFake())
    texto = " ".join(coletar_textos(view))

    assert "Perguntas do perfil" in texto
    assert "Selecionar foto" in texto
    assert "16 MB" in texto
    assert "URL da foto" not in texto


def test_validar_imagem_perfil_aceita_extensoes_e_limite():
    assert validar_imagem_perfil("foto.png", MAX_PROFILE_IMAGE_BYTES) == (True, "")
    assert validar_imagem_perfil("foto.webp", MAX_PROFILE_IMAGE_BYTES - 1) == (True, "")

    valido_extensao, mensagem_extensao = validar_imagem_perfil("foto.gif", 10)
    valido_tamanho, mensagem_tamanho = validar_imagem_perfil(
        "foto.jpg",
        MAX_PROFILE_IMAGE_BYTES + 1,
    )

    assert valido_extensao is False
    assert "png" in mensagem_extensao
    assert valido_tamanho is False
    assert "16 MB" in mensagem_tamanho


def test_gerar_caminho_upload_imagem_usa_email_seguro():
    caminho = gerar_caminho_upload_imagem(
        "Fellipe.Teste+App@Example.COM",
        "rosto.jpeg",
        token="abc123",
    )

    assert caminho == "uploads/profile_images/fellipe_teste_app_example_com/abc123.jpeg"


def test_perfil_publico_completo_exige_foto_e_campos_publicos():
    incompleto = {
        "nome": "Fellipe",
        "idade": 25,
        "foto_url": "",
        "descricao": "Bio",
        "localizacao": "Recife",
        "cargo": "Dev",
    }
    completo = {
        **incompleto,
        "foto_url": "uploads/profile_images/fellipe/foto.jpg",
    }

    assert perfil_publico_completo(incompleto) is False
    assert campos_faltantes_perfil(incompleto) == ["foto_url"]
    assert perfil_publico_completo(completo) is True

import pytest

pytest.importorskip("flet")

from src.views.match_view import matchView, montar_perfil_match


def test_montar_perfil_match_prefere_match_id_salvo_ao_id_sqlite():
    perfil = montar_perfil_match(
        {
            "id": 1,
            "match_id": "user_beatriz",
            "nome": "Beatriz Lima",
            "afinidade": "88%",
            "dados_match": {
                "id": "user_beatriz",
                "match_id": "user_beatriz",
                "idade": 19,
                "descricao": "Perfil salvo",
            },
        }
    )

    assert perfil["id"] == "user_beatriz"
    assert perfil["match_id"] == "user_beatriz"
    assert perfil["descricao"] == "Perfil salvo"
    assert "afinidade" not in perfil


class PageFake:
    def __init__(self, email, perfil_publico=None):
        self.usuario_logado = {"email": email, "nome": "Teste"}
        self.match_result = None
        self.match_deck = None
        self.match_active_tab = "perfis"
        self.height = 800
        if perfil_publico is not None:
            self.perfil_publico = perfil_publico

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


def test_formulario_mock_aparece_apenas_para_admin():
    view_admin = matchView(PageFake("rafaellapipucos@gmail.com"))
    view_comum = matchView(PageFake("fellipe@example.com"))

    textos_admin = coletar_textos(view_admin)
    textos_comum = coletar_textos(view_comum)

    assert "Adicionar perfil mock" in textos_admin
    assert "Adicionar perfil mock" not in textos_comum


def test_match_view_nao_exibe_porcentagem_de_compatibilidade():
    page = PageFake("fellipe@example.com")
    page.match_deck = [
        {
            "id": "user_maria",
            "match_id": "user_maria",
            "nome": "Maria",
            "idade": 22,
            "descricao": "Perfil com muita conversa boa.",
            "localizacao": "Recife",
            "cargo": "Designer",
            "imagem": "foto.jpg",
            "afinidade": "99%",
        }
    ]

    view = matchView(page)
    textos = coletar_textos(view)

    assert "99%" not in textos
    assert "afinidade" not in " ".join(textos).lower()


def test_match_view_bloqueia_descoberta_com_perfil_incompleto():
    page = PageFake(
        "fellipe@example.com",
        perfil_publico={
            "nome": "Fellipe",
            "idade": 25,
            "foto_url": "",
            "descricao": "Bio",
            "localizacao": "Recife",
            "cargo": "Dev",
        },
    )

    view = matchView(page)
    texto = " ".join(coletar_textos(view))

    assert "Complete seu perfil" in texto
    assert "Completar perfil" in texto
    assert "foto" in texto
    assert "URL da foto" not in texto

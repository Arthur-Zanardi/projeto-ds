"""Teste de renderização da tela de login (frontend Flet)."""
import pytest

pytest.importorskip("flet")

from src.views.login_view import loginView  # noqa: E402


class PageFake:
    def __init__(self):
        self.route = "/login"
        self.usuario_logado = None
        self.match_deck = None

    def update(self):
        return None

    def go(self, route):
        self.route = route


def _coletar_textos(control):
    textos = []
    if isinstance(control, str):
        return [control]
    valor = getattr(control, "value", None)
    if isinstance(valor, str):
        textos.append(valor)
    conteudo = getattr(control, "content", None)
    if conteudo is not None:
        textos.extend(_coletar_textos(conteudo))
    for filho in getattr(control, "controls", []) or []:
        textos.extend(_coletar_textos(filho))
    return textos


def test_login_view_renderiza():
    view = loginView(PageFake())
    textos = _coletar_textos(view)
    assert any("Match.AI" in t for t in textos)

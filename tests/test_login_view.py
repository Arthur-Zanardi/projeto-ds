from src.controllers.login_controller import LoginController
from src.views.login_view import loginView


class PageFake:
    def __init__(self):
        self.route = "/login"
        self.usuario_logado = None
        self.match_deck = None

    def update(self):
        return None

    def go(self, route):
        self.route = route


class ControllerFake:
    def realizar_login(self, email, senha):
        return {"email": email, "nome": "Teste"}

    def realizar_cadastro(self, **kwargs):
        self.cadastro = kwargs
        return True


class RepoFake:
    def __init__(self):
        self.chamada = None

    def criar_usuario(self, **kwargs):
        self.chamada = kwargs
        return True

    def buscar_usuario_por_email(self, email):
        return None


def coletar_textos(control):
    textos = []

    if isinstance(control, str):
        return [control]

    for attr in ("value", "content", "label", "hint_text", "tooltip"):
        value = getattr(control, attr, None)
        if isinstance(value, str):
            textos.append(value)
        elif value is not None and attr == "content":
            textos.extend(coletar_textos(value))

    for child in getattr(control, "controls", []) or []:
        textos.extend(coletar_textos(child))

    return textos


def test_login_view_cadastro_nao_renderiza_perguntas_de_perfil():
    view = loginView(PageFake(), ControllerFake())
    texto = " ".join(coletar_textos(view))

    assert "seu@email.com" in texto
    assert "Senha" in texto
    assert "Como voce se chama?" not in texto
    assert "URL da foto" not in texto
    assert "Uma bio curta sobre voce" not in texto


def test_login_controller_cadastro_usa_apenas_email_e_senha():
    repo = RepoFake()
    controller = LoginController(repo)

    assert controller.realizar_cadastro(email="fellipe@example.com", senha_pura="segredo")
    assert repo.chamada == {
        "email": "fellipe@example.com",
        "senha_pura": "segredo",
        "nome": None,
        "idade": None,
        "foto_url": None,
        "descricao": None,
        "localizacao": None,
        "cargo": None,
    }

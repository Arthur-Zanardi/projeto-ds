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


class PageFake:
    def __init__(self, email):
        self.usuario_logado = {"email": email, "nome": "Teste"}
        self.match_result = None
        self.match_active_tab = "perfis"
        self.height = 800

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

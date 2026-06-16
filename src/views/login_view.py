import flet as ft

from src.controllers.login_controller import LoginController
from src.services import api_client
from src.views.app_layout import BG_MUTED, BORDER, CORAL, PINK, TEXT_MAIN, TEXT_MUTED


def loginView(page: ft.Page, controller: LoginController) -> ft.View:
    state = {"mode": "login"}

    title_text = ft.Text(
        "Bem-vindo de volta",
        size=28,
        weight=ft.FontWeight.BOLD,
        color=TEXT_MAIN,
    )
    subtitle_text = ft.Text(
        "Continue sua entrevista e descubra conexoes reais.",
        color=TEXT_MUTED,
        size=14,
    )
    error_text = ft.Text("", color=ft.Colors.RED_500, size=12, visible=False)

    txt_email = ft.TextField(hint_text="seu@email.com", border_radius=14)
    txt_senha = ft.TextField(
        hint_text="Senha",
        password=True,
        can_reveal_password=True,
        border_radius=14,
    )

    register_hint = ft.AnimatedSwitcher(
        content=ft.Container(),
        duration=250,
        reverse_duration=180,
        transition=ft.AnimatedSwitcherTransition.FADE,
    )

    cta_text = ft.Text("Entrar", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=16)
    cta_icon = ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.WHITE, size=20)

    def set_error(message: str):
        error_text.value = message
        error_text.visible = bool(message)
        page.update()

    def change_mode(new_mode):
        state["mode"] = new_mode
        set_error("")

        if new_mode == "login":
            title_text.value = "Bem-vindo de volta"
            subtitle_text.value = "Continue sua entrevista e descubra conexoes reais."
            register_hint.content = ft.Container()
            cta_text.value = "Entrar"
            cta_icon.name = ft.Icons.ARROW_FORWARD
            login_btn.bgcolor = CORAL
            login_btn.color = ft.Colors.WHITE
            register_btn.bgcolor = ft.Colors.TRANSPARENT
            register_btn.color = TEXT_MUTED
        else:
            title_text.value = "Crie sua conta"
            subtitle_text.value = "Entre com e-mail e senha. Seu perfil publico vem logo depois."
            register_hint.content = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PERSON_OUTLINE, color=PINK, size=20),
                        ft.Text(
                            "Depois do cadastro voce completa foto, idade, cidade e bio na aba Perfil.",
                            color=TEXT_MUTED,
                            size=12,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor="#FFF1F6",
                border=ft.Border.all(1, "#FFD3E4"),
                border_radius=14,
                padding=12,
            )
            cta_text.value = "Criar conta"
            cta_icon.name = ft.Icons.AUTO_AWESOME
            register_btn.bgcolor = CORAL
            register_btn.color = ft.Colors.WHITE
            login_btn.bgcolor = ft.Colors.TRANSPARENT
            login_btn.color = TEXT_MUTED

        page.update()

    login_btn = ft.Button(
        content="Entrar",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=CORAL,
            color=ft.Colors.WHITE,
            elevation=0,
        ),
        on_click=lambda _: change_mode("login"),
        expand=True,
    )

    register_btn = ft.Button(
        content="Criar conta",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.TRANSPARENT,
            color=TEXT_MUTED,
            elevation=0,
        ),
        on_click=lambda _: change_mode("register"),
        expand=True,
    )

    def autenticar_usuario(usuario, rota="/chat"):
        page.usuario_logado = usuario
        page.match_deck = None
        page.go(rota)

    async def submeter_formulario(_):
        set_error("")
        email = (txt_email.value or "").strip().lower()
        senha = txt_senha.value or ""

        if not email or not senha:
            set_error("Preencha e-mail e senha.")
            return

        if state["mode"] == "login":
            resultado = await api_client.login(email, senha)
            if resultado.get("sucesso"):
                autenticar_usuario(resultado["usuario"])
            else:
                set_error(resultado.get("mensagem") or "E-mail ou senha incorretos.")
            return

        resultado = await api_client.registrar(email, senha)
        if not resultado.get("sucesso"):
            set_error(
                resultado.get("mensagem")
                or "Este e-mail ja esta cadastrado ou os dados sao invalidos."
            )
            return

        autenticar_usuario(resultado["usuario"], "/profile")

    tabs_container = ft.Container(
        content=ft.Row([login_btn, register_btn], spacing=0),
        bgcolor=BG_MUTED,
        border_radius=14,
        padding=4,
        margin=ft.Margin(0, 20, 0, 18),
    )

    cta_button = ft.Container(
        content=ft.Row(
            [cta_icon, cta_text],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        ),
        gradient=ft.LinearGradient(colors=[CORAL, PINK]),
        height=54,
        border_radius=16,
        on_click=submeter_formulario,
        margin=ft.Margin(0, 12, 0, 0),
    )

    form = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.WHITE, size=22),
                            gradient=ft.LinearGradient(colors=[CORAL, PINK]),
                            width=42,
                            height=42,
                            border_radius=14,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Text("Match.AI", size=18, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                title_text,
                subtitle_text,
                tabs_container,
                register_hint,
                txt_email,
                txt_senha,
                error_text,
                cta_button,
            ],
            spacing=10,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=20,
        padding=22,
        width=460,
    )

    return ft.View(
        route="/login",
        padding=20,
        bgcolor="#FAFAFA",
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                content=form,
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        ],
    )

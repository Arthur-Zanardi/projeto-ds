# src/views/login_view.py
import flet as ft
from src.controllers.login_controller import LoginController

def loginView(page: ft.Page, controller: LoginController) -> ft.View:
    state = {"mode": "login"}

    CORAL = "#FF7F50"
    PINK = "#FF69B4"
    BG_INPUT = "#F3F4F6"
    TEXT_MUTED = "#6B7280"
    LINE_DIVIDER = "#E5E7EB"
    TEXT_MAIN = "#111827"

    title_text = ft.Text("Bem-vindo de volta", size=30, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
    subtitle_text = ft.Text("Continue de onde parou e encontre o seu match.", color=TEXT_MUTED, size=14)

    # --- CAMPOS DE ENTRADA CONFIGURADOS COMO VARIÁVEIS ---
    txt_nome = ft.TextField(
        hint_text="Como você se chama?",
        border_radius=16,
        bgcolor=BG_INPUT,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=CORAL,
        text_size=15,
        height=52,
        content_padding=16
    )

    txt_email = ft.TextField(
        hint_text="seu@email.com",
        border_radius=16,
        bgcolor=BG_INPUT,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=CORAL,
        text_size=15,
        height=52,
        content_padding=16
    )

    txt_senha = ft.TextField(
        hint_text="••••••••",
        password=True,
        can_reveal_password=True,
        border_radius=16,
        bgcolor=BG_INPUT,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=CORAL,
        text_size=15,
        height=52,
        content_padding=16
    )

    # Containers que envolvem os campos na árvore de componentes
    name_field = ft.Container(
        content=ft.Column([
            ft.Text("Seu nome", size=12, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
            txt_nome
        ], spacing=5),
        visible=False,
        margin=ft.margin.only(bottom=12)
    )

    email_field = ft.Container(
        content=ft.Column([
            ft.Text("E-mail", size=12, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
            txt_email
        ], spacing=5),
        margin=ft.margin.only(bottom=12)
    )

    password_field = ft.Container(
        content=ft.Column([
            ft.Text("Senha", size=12, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
            txt_senha
        ], spacing=5),
        margin=ft.margin.only(bottom=12)
    )

    forgot_password = ft.Container(
        content=ft.Text("Esqueci minha senha", size=13, color=CORAL, weight=ft.FontWeight.W_500),
        alignment=ft.Alignment(1.0, 0.0), 
        visible=True,
        margin=ft.margin.only(bottom=24)
    )

    cta_text = ft.Text("Entrar", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=16)
    cta_icon = ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.WHITE, size=20)

    def change_mode(new_mode):
        state["mode"] = new_mode
        if new_mode == "login":
            title_text.value = "Bem-vindo de volta"
            subtitle_text.value = "Continue de onde parou e encontre o seu match."
            name_field.visible = False
            forgot_password.visible = True
            cta_text.value = "Entrar"
            cta_icon.name = ft.Icons.ARROW_FORWARD
            login_btn.bgcolor = CORAL
            login_btn.color = ft.Colors.WHITE
            register_btn.bgcolor = ft.Colors.TRANSPARENT
            register_btn.color = TEXT_MUTED
        else:
            title_text.value = "Encontre sua conexão"
            subtitle_text.value = "Crie sua conta e deixe a IA encontrar quem combina com você."
            name_field.visible = True
            forgot_password.visible = False
            cta_text.value = "Criar conta e iniciar entrevista"
            cta_icon.name = ft.Icons.AUTO_AWESOME
            register_btn.bgcolor = CORAL
            register_btn.color = ft.Colors.WHITE
            login_btn.bgcolor = ft.Colors.TRANSPARENT
            login_btn.color = TEXT_MUTED
        page.update()

    login_btn = ft.ElevatedButton(
        "Entrar",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), bgcolor=CORAL, color=ft.Colors.WHITE, elevation=0),
        on_click=lambda _: change_mode("login"),
        expand=True
    )

    register_btn = ft.ElevatedButton(
        "Criar conta",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), bgcolor=ft.Colors.TRANSPARENT, color=TEXT_MUTED, elevation=0),
        on_click=lambda _: change_mode("register"),
        expand=True
    )

    tabs_container = ft.Container(
        content=ft.Row([login_btn, register_btn], spacing=0),
        bgcolor=BG_INPUT,
        border_radius=14,
        padding=4,
        margin=ft.margin.only(bottom=28)
    )

    # --- FUNÇÃO DE SUBMIT CONECTADA AO CONTROLLER ---
    async def submeter_formulario(e):
        email = txt_email.value.strip()
        senha = txt_senha.value

        # Componente de feedback rápido (Banner de erro)
        def mostrar_erro(mensagem):
            page.snack_bar = ft.SnackBar(ft.Text(mensagem), bgcolor=ft.Colors.RED_ACCENT)
            page.snack_bar.open = True
            page.update()

        if state["mode"] == "login":
                usuario = controller.realizar_login(email, senha)
                if usuario:
                    # === NOVA FORMA DE SALVAR A SESSÃO ===
                    page.usuario_logado = usuario
                    
                    page.views.pop()
                    await page.push_route("/chat")
                else:
                    mostrar_erro("E-mail ou senha incorretos.")
                    
        else:
                nome = txt_nome.value.strip()
                if not nome:
                    mostrar_erro("Por favor, preencha o seu nome.")
                    return

                sucesso = controller.realizar_cadastro(nome, email, senha)
                if sucesso:
                    usuario = controller.realizar_login(email, senha)
                    
                    # === NOVA FORMA DE SALVAR A SESSÃO ===
                    page.usuario_logado = usuario
                    
                    page.views.pop()
                    await page.push_route("/chat")
                else:
                    mostrar_erro("Este e-mail já está cadastrado ou os dados são inválidos.")

    cta_button = ft.Container(
        content=ft.Row([cta_icon, cta_text], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        gradient=ft.LinearGradient(begin=ft.Alignment(-1.0, 0.0), end=ft.Alignment(1.0, 0.0), colors=[CORAL, PINK]),
        height=56,
        border_radius=16,
        on_click=submeter_formulario, # <-- Executa a nossa validação
        margin=ft.margin.only(bottom=24)
    )

    # (O restante dos componentes visuais permanece o mesmo que você fez)
    divider_row = ft.Row([
        ft.Divider(expand=True, color=LINE_DIVIDER, height=1),
        ft.Text("ou continue com", size=12, color=TEXT_MUTED),
        ft.Divider(expand=True, color=LINE_DIVIDER, height=1),
    ], alignment=ft.MainAxisAlignment.CENTER, margin=ft.margin.only(bottom=24))

    social_buttons = ft.Row([
        ft.OutlinedButton("Google", icon=ft.Icons.G_MOBILEDATA, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), color=TEXT_MAIN), expand=True, height=48),
        ft.OutlinedButton("Apple", icon=ft.Icons.APPLE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), color=TEXT_MAIN), expand=True, height=48)
    ], spacing=12, margin=ft.margin.only(bottom=28))

    terms_text = ft.Text(spans=[ft.TextSpan("Ao continuar, você concorda com nossos "), ft.TextSpan("Termos de Uso", ft.TextStyle(color=CORAL, weight=ft.FontWeight.BOLD)), ft.TextSpan(" e "), ft.TextSpan("Política de Privacidade", ft.TextStyle(color=CORAL, weight=ft.FontWeight.BOLD))], size=12, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)

    return ft.View(
        route="/login", # Rota correta inicial da View
        padding=24,
        bgcolor="#FAFAFA",
        controls=[
            ft.Container(content=ft.Row([ft.Container(content=ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.WHITE, size=22), gradient=ft.LinearGradient(colors=[CORAL, PINK]), width=42, height=42, border_radius=14, alignment=ft.Alignment(0.0, 0.0)), ft.Text("MatchAi", size=24, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)], spacing=12), margin=ft.margin.only(top=30, bottom=36)),
            title_text,
            ft.Container(content=subtitle_text, margin=ft.margin.only(bottom=28)),
            tabs_container,
            name_field,
            email_field,
            password_field,
            forgot_password,
            cta_button,
            divider_row,
            social_buttons,
            ft.Container(content=terms_text, alignment=ft.Alignment(0.0, 0.0))
        ],
        scroll=ft.ScrollMode.AUTO,
    )
import asyncio

import flet as ft

from src.services.api_client import carregar_historico, dar_match, enviar_mensagem_chat
from src.views.app_layout import (
    BG_MUTED,
    CORAL,
    PINK,
    TEXT_MAIN,
    TEXT_MUTED,
    authenticated_view,
)


def chatView(page):
    mensagens_usuario = []
    usuario_logado = getattr(page, "usuario_logado", None)

    gradient = ft.LinearGradient(colors=[CORAL, PINK])
    status_text = ft.Text("", size=12, color=TEXT_MUTED)

    messages_view = ft.ListView(expand=True, spacing=8, auto_scroll=True, padding=14)
    field = ft.TextField(
        hint_text="Conte algo sobre voce...",
        expand=True,
        on_submit=lambda event: send_clicked(event),
        autofocus=True,
        border_radius=14,
    )

    def add_message(text, is_me=True):
        align = ft.CrossAxisAlignment.END if is_me else ft.CrossAxisAlignment.START
        text_color = ft.Colors.WHITE if is_me else TEXT_MAIN
        bg_gradient = gradient if is_me else None
        bg_solid = None if is_me else ft.Colors.WHITE

        messages_view.controls.append(
            ft.Column(
                horizontal_alignment=align,
                controls=[
                    ft.Container(
                        content=ft.Text(text, size=15, color=text_color),
                        gradient=bg_gradient,
                        bgcolor=bg_solid,
                        border=ft.Border.all(1, "#FFFFFF") if not is_me else None,
                        padding=12,
                        border_radius=18,
                    )
                ],
            )
        )
        try:
            messages_view.update()
        except (AssertionError, RuntimeError):
            pass

    def append_message(remetente, mensagem):
        add_message(mensagem, is_me=remetente == "usuario")

    def set_status(mensagem, color=TEXT_MUTED):
        status_text.value = mensagem
        status_text.color = color
        try:
            status_text.update()
        except (AssertionError, RuntimeError):
            pass

    def set_match_button_loading(is_loading):
        match_button.disabled = is_loading
        match_button.content = "Buscando..." if is_loading else "Dar match"
        match_button.icon = ft.Icons.HOURGLASS_TOP if is_loading else ft.Icons.FAVORITE
        try:
            match_button.update()
        except (AssertionError, RuntimeError):
            pass

    def send_clicked(_):
        texto_usuario = (field.value or "").strip()
        if not texto_usuario:
            return

        mensagens_usuario.append(texto_usuario)
        add_message(texto_usuario, is_me=True)
        field.value = ""
        field.focus()
        page.update()
        receive_message(texto_usuario)

    async def receive_message_async(texto_enviado):
        response = await enviar_mensagem_chat(texto_enviado, usuario_logado)
        add_message(response, is_me=False)

    def receive_message(texto_enviado):
        if hasattr(page, "run_task"):
            page.run_task(receive_message_async, texto_enviado)
        else:
            asyncio.get_running_loop().create_task(receive_message_async(texto_enviado))

    async def match_clicked_async():
        set_match_button_loading(True)
        try:
            resultado = await dar_match(mensagens_usuario, usuario_logado)
            if resultado.get("sucesso"):
                page.match_deck = resultado.get("matches", [])
                page.match_result = resultado.get("match")
                set_status("Perfis encontrados. Abrindo descoberta...", CORAL)
                page.go("/match")
                return

            if resultado.get("perfil_incompleto"):
                set_status("Complete seu perfil para liberar a descoberta.", ft.Colors.RED_500)
                page.go("/profile")
                return

            set_status(resultado.get("mensagem", "Ainda nao foi possivel encontrar um match."))
        finally:
            set_match_button_loading(False)

    def match_clicked(_):
        if hasattr(page, "run_task"):
            page.run_task(match_clicked_async)
        else:
            asyncio.get_running_loop().create_task(match_clicked_async())

    async def load_saved_messages():
        historico = await carregar_historico(usuario_logado)

        for item in historico:
            remetente = item.get("remetente")
            mensagem = item.get("mensagem")
            if remetente in ("usuario", "ia") and mensagem:
                if remetente == "usuario":
                    mensagens_usuario.append(mensagem)
                append_message(remetente, mensagem)

    if hasattr(page, "run_task"):
        page.run_task(load_saved_messages)
    else:
        asyncio.get_running_loop().create_task(load_saved_messages())

    send_button = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SEND,
            icon_color=ft.Colors.WHITE,
            on_click=send_clicked,
            tooltip="Enviar",
        ),
        gradient=gradient,
        shape=ft.BoxShape.CIRCLE,
    )

    match_button = ft.FilledButton(
        content="Dar match",
        icon=ft.Icons.FAVORITE,
        on_click=match_clicked,
        style=ft.ButtonStyle(bgcolor=PINK, color=ft.Colors.WHITE),
    )

    header_actions = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(
                    "Converse com a IA ate seu perfil vetorial ficar mais rico.",
                    size=12,
                    color=TEXT_MUTED,
                    expand=True,
                ),
                ft.TextButton(
                    content="Meu perfil",
                    icon=ft.Icons.PERSON,
                    on_click=lambda _: page.go("/profile"),
                    style=ft.ButtonStyle(color=CORAL),
                ),
                match_button,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(14, 8, 14, 8),
        bgcolor=ft.Colors.WHITE,
    )

    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_button]),
        bgcolor=ft.Colors.WHITE,
        padding=ft.Padding(10, 8, 10, 8),
    )

    content = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            header_actions,
            ft.Container(content=status_text, padding=ft.Padding(18, 4, 18, 4)),
            ft.Container(content=messages_view, expand=True, bgcolor=BG_MUTED),
            sender_container,
        ],
    )

    return authenticated_view(
        page,
        "/chat",
        "Entrevista com IA",
        content,
        subtitle="As respostas alimentam seus matches.",
    )

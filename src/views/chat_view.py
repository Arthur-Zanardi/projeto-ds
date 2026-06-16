import asyncio

import flet as ft

from src.services.api_client import (
    carregar_historico,
    criar_match,
    dar_match,
    enviar_mensagem_chat,
)


def chatView(page):
    mensagens_usuario = []
    usuario_logado = getattr(page, "usuario_logado", None)

    def goto_profile_screen(_):
        page.go("/profile")

    def add_message(text, is_me=True):
        align = ft.CrossAxisAlignment.END if is_me else ft.CrossAxisAlignment.START
        text_color = ft.Colors.WHITE if is_me else ft.Colors.BLACK_87

        bg_gradient = new_gradient if is_me else None
        bg_solid = None if is_me else ft.Colors.BLACK_12

        messages_view.controls.append(
            ft.Column(
                horizontal_alignment=align,
                controls=[
                    ft.Container(
                        content=ft.Text(f"{text}", size=16, color=text_color),
                        gradient=bg_gradient,
                        bgcolor=bg_solid,
                        padding=12,
                        border_radius=18,
                    )
                ],
            )
        )
        messages_view.update()

    def append_message(remetente, mensagem):
        add_message(mensagem, is_me=remetente == "usuario")

    def set_match_button_loading(is_loading):
        match_button.disabled = is_loading
        match_button.content = "Buscando..." if is_loading else "Dar match"
        match_button.icon = ft.Icons.HOURGLASS_TOP if is_loading else ft.Icons.FAVORITE
        match_button.update()

    def send_clicked(_):
        texto_usuario = field.value.strip()
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
            try:
                asyncio.get_running_loop().create_task(
                    receive_message_async(texto_enviado)
                )
            except RuntimeError:
                pass

    async def match_clicked_async():
        set_match_button_loading(True)
        navegou_para_match = False

        try:
            resultado = await dar_match(mensagens_usuario, usuario_logado)

            if resultado.get("sucesso"):
                page.match_result = resultado["match"]
                await criar_match(resultado["match"], usuario_logado)
                set_match_button_loading(False)
                navegou_para_match = True
                page.match_active_tab = "perfis"
                page.go("/match")
                return

            texto_match = resultado.get(
                "mensagem",
                "Ainda nao foi possivel encontrar um match.",
            )

            append_message("ia", texto_match)
        finally:
            if not navegou_para_match:
                set_match_button_loading(False)

    def match_clicked(_):
        if hasattr(page, "run_task"):
            page.run_task(match_clicked_async)
        else:
            try:
                asyncio.get_running_loop().create_task(match_clicked_async())
            except RuntimeError:
                pass

    new_gradient = ft.LinearGradient(
        begin=ft.alignment.Alignment(-1, 0),
        end=ft.alignment.Alignment(1, 0),
        colors=["#e63946", "#d63384"],
    )

    field = ft.TextField(
        label="Digite aqui a sua mensagem",
        expand=True,
        on_submit=send_clicked,
        autofocus=True,
    )

    send_button = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SEND,
            icon_color=ft.Colors.WHITE,
            on_click=send_clicked,
        ),
        gradient=new_gradient,
        shape=ft.BoxShape.CIRCLE,
    )

    match_button = ft.FilledButton(
        content="Dar match",
        icon=ft.Icons.FAVORITE,
        on_click=match_clicked,
        style=ft.ButtonStyle(
            color="#fff0f3",
            bgcolor="#d63384",
        ),
    )

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
    )

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
        try:
            asyncio.get_running_loop().create_task(load_saved_messages())
        except RuntimeError:
            pass

    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Entrevista com IA",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLACK_87,
                        ),
                        ft.TextButton(
                            content="Ver Meu Perfil",
                            icon=ft.Icons.ARROW_FORWARD,
                            on_click=goto_profile_screen,
                            style=ft.ButtonStyle(color="#d63384"),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[match_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=6,
        ),
        padding=ft.Padding.only(top=10, bottom=10, left=20, right=10),
    )

    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_button]),
        height=max(50, page.height * 0.08),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(horizontal=10),
    )

    column = ft.Column(
        expand=True,
        controls=[
            header,
            messages_view,
            sender_container,
        ],
    )

    return ft.View(
        route="/chat",
        controls=[column],
        bgcolor=ft.Colors.PINK_50,
    )

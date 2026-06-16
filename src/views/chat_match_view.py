import asyncio

import flet as ft

from src.services.api_client import (
    carregar_historico_match,
    criar_match,
    salvar_mensagem_match,
)
from src.views.match_view import (
    BORDER,
    BG_MAIN,
    BG_MUTED,
    CORAL,
    PINK,
    TEXT_MAIN,
    TEXT_MUTED,
    montar_perfil_match,
    perfil_para_payload,
)


def matchChatView(page, match_name=None, match_id=None):
    match_result = getattr(page, "match_result", {}) or {}
    if match_name:
        match_result["nome"] = match_name
    if match_id:
        match_result["id"] = match_id

    perfil = montar_perfil_match(match_result)
    match_id_ativo = (
        match_id
        or getattr(page, "active_match_id", None)
        or perfil.get("id")
        or perfil.get("match_id")
    )
    perfil["id"] = match_id_ativo
    perfil["match_id"] = match_id_ativo

    state = {
        "match_salvo": False,
        "respostas_enviadas": 0,
        "carregando": True,
    }

    new_gradient = ft.LinearGradient(
        begin=ft.alignment.Alignment(-1, 0),
        end=ft.alignment.Alignment(1, 0),
        colors=[CORAL, PINK],
    )

    status_text = ft.Text("Carregando conversa...", size=12, color=TEXT_MUTED)

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )

    field = ft.TextField(
        label=f"Mensagem para {perfil['nome']}",
        expand=True,
        on_submit=lambda event: send_clicked(event),
        autofocus=True,
    )

    def goto_profile_screen(_):
        page.match_active_tab = "perfis"
        page.match_result = perfil_para_payload(perfil)
        page.go("/match")

    def goto_conversations(_):
        page.match_active_tab = "conversas"
        page.go("/match")

    def set_status(mensagem, color=TEXT_MUTED):
        status_text.value = mensagem
        status_text.color = color
        try:
            status_text.update()
        except AssertionError:
            pass

    def add_message(text, is_me=True):
        align = ft.CrossAxisAlignment.END if is_me else ft.CrossAxisAlignment.START
        text_color = ft.Colors.WHITE if is_me else TEXT_MAIN
        bg_gradient = new_gradient if is_me else None
        bg_solid = None if is_me else ft.Colors.WHITE
        border = None if is_me else ft.border.all(1, BORDER)

        messages_view.controls.append(
            ft.Column(
                horizontal_alignment=align,
                controls=[
                    ft.Container(
                        content=ft.Text(text, size=15, color=text_color),
                        gradient=bg_gradient,
                        bgcolor=bg_solid,
                        border=border,
                        padding=12,
                        border_radius=18,
                    )
                ],
            )
        )
        try:
            messages_view.update()
        except AssertionError:
            pass

    def append_message(item):
        remetente = item.get("remetente")
        mensagem = item.get("mensagem")
        if mensagem:
            add_message(mensagem, is_me=remetente == "usuario")

    def resposta_mock(texto_usuario):
        respostas = perfil.get("respostas") or [
            "Gostei disso. Me conta mais com calma.",
            "Esse assunto combina com a nossa afinidade.",
            "Curti a pergunta. Quero saber como voce pensa sobre isso.",
        ]
        indice = state["respostas_enviadas"] % len(respostas)
        state["respostas_enviadas"] += 1
        texto_usuario = texto_usuario.lower()

        if "oi" in texto_usuario or "ola" in texto_usuario:
            return f"Oi! Eu sou {perfil['nome']}. Bom te ver por aqui."

        return respostas[indice]

    async def garantir_match_salvo():
        if state["match_salvo"]:
            return True

        resultado = await criar_match(perfil_para_payload(perfil))
        if resultado.get("sucesso"):
            state["match_salvo"] = True
            return True

        set_status(
            resultado.get("mensagem", "Nao foi possivel salvar o match."),
            ft.Colors.RED_500,
        )
        return False

    async def load_saved_messages():
        state["carregando"] = True
        if not await garantir_match_salvo():
            state["carregando"] = False
            return

        historico = await carregar_historico_match(match_id_ativo)
        messages_view.controls.clear()

        if historico:
            for item in historico:
                append_message(item)
            set_status("Conversa carregada do banco.", CORAL)
        else:
            saudacao = (
                f"Oi, eu sou {perfil['nome']}. Vi nosso match e fiquei curiosa "
                "para conversar."
            )
            add_message(saudacao, is_me=False)
            await salvar_mensagem_match(match_id_ativo, saudacao, "match")
            set_status("Conversa iniciada e salva no banco.", CORAL)

        state["carregando"] = False

    async def enviar_mensagem_async(texto_usuario):
        if not await garantir_match_salvo():
            return

        resultado = await salvar_mensagem_match(
            match_id_ativo,
            texto_usuario,
            "usuario",
        )
        if not resultado.get("sucesso"):
            set_status(resultado.get("mensagem", "Falha ao salvar mensagem."), ft.Colors.RED_500)
            return

        resposta = resposta_mock(texto_usuario)
        add_message(resposta, is_me=False)
        resposta_salva = await salvar_mensagem_match(
            match_id_ativo,
            resposta,
            "match",
        )

        if resposta_salva.get("sucesso"):
            set_status("Mensagem salva no banco.", CORAL)
        else:
            set_status(
                resposta_salva.get("mensagem", "Falha ao salvar resposta."),
                ft.Colors.RED_500,
            )

    def send_clicked(_):
        texto_usuario = (field.value or "").strip()
        if not texto_usuario:
            return

        add_message(texto_usuario, is_me=True)
        field.value = ""
        field.focus()
        page.update()

        if hasattr(page, "run_task"):
            page.run_task(enviar_mensagem_async, texto_usuario)
        else:
            asyncio.get_running_loop().create_task(
                enviar_mensagem_async(texto_usuario)
            )

    send_button = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SEND,
            icon_color=ft.Colors.WHITE,
            on_click=send_clicked,
            tooltip="Enviar",
        ),
        gradient=new_gradient,
        shape=ft.BoxShape.CIRCLE,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=TEXT_MAIN,
                    on_click=goto_conversations,
                    tooltip="Conversas",
                ),
                ft.Container(
                    content=ft.Image(
                        src=perfil["imagem"],
                        fit=ft.BoxFit.COVER,
                        width=46,
                        height=46,
                    ),
                    width=46,
                    height=46,
                    border_radius=23,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            perfil["nome"],
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_MAIN,
                        ),
                        ft.Text(
                            perfil.get("afinidade") or "Match salvo",
                            size=12,
                            color=PINK,
                        ),
                    ],
                    expand=True,
                    spacing=0,
                ),
                ft.TextButton(
                    content="Perfil",
                    icon=ft.Icons.PERSON,
                    on_click=goto_profile_screen,
                    style=ft.ButtonStyle(color=CORAL),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(top=10, left=8, right=10, bottom=8),
        bgcolor=BG_MAIN,
    )

    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_button]),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(top=ft.BorderSide(1, BORDER)),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    column = ft.Column(
        expand=True,
        controls=[
            header,
            ft.Container(
                content=status_text,
                padding=ft.padding.symmetric(horizontal=20),
            ),
            ft.Container(
                content=messages_view,
                expand=True,
                bgcolor=BG_MUTED,
            ),
            sender_container,
        ],
        spacing=0,
    )

    if hasattr(page, "run_task"):
        page.run_task(load_saved_messages)
    else:
        asyncio.get_running_loop().create_task(load_saved_messages())

    return ft.View(
        route="/chatmatch",
        controls=[column],
        bgcolor=BG_MAIN,
    )

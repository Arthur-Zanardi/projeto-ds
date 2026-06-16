import asyncio

import flet as ft

from src.services.api_client import carregar_historico_match, salvar_mensagem_match
from src.views.app_layout import (
    BG_MAIN,
    BG_MUTED,
    BORDER,
    CORAL,
    PINK,
    TEXT_MAIN,
    TEXT_MUTED,
    authenticated_view,
)
from src.views.match_view import montar_perfil_match, perfil_para_payload


def matchChatView(page, match_name=None, match_id=None):
    usuario_logado = getattr(page, "usuario_logado", None)
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
    sugestoes = (
        getattr(page, "match_sugestoes", None)
        or perfil.get("sugestoes_inicio")
        or []
    )

    state = {"respostas_enviadas": 0, "carregando": True}
    gradient = ft.LinearGradient(colors=[CORAL, PINK])
    status_text = ft.Text("Carregando conversa...", size=12, color=TEXT_MUTED)

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
        padding=ft.Padding(14, 10, 14, 10),
    )
    field = ft.TextField(
        hint_text=f"Mensagem para {perfil['nome']}",
        expand=True,
        on_submit=lambda event: send_clicked(event),
        autofocus=True,
        border_radius=14,
    )

    pending_starter = getattr(page, "pending_starter_message", None)
    if pending_starter:
        field.value = pending_starter
        page.pending_starter_message = None

    def set_status(mensagem, color=TEXT_MUTED):
        status_text.value = mensagem
        status_text.color = color
        try:
            status_text.update()
        except (AssertionError, RuntimeError):
            pass

    def add_message(text, is_me=True):
        align = ft.CrossAxisAlignment.END if is_me else ft.CrossAxisAlignment.START
        text_color = ft.Colors.WHITE if is_me else TEXT_MAIN
        bg_gradient = gradient if is_me else None
        bg_solid = None if is_me else ft.Colors.WHITE
        border = None if is_me else ft.Border.all(1, BORDER)

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
        except (AssertionError, RuntimeError):
            pass

    def append_message(item):
        remetente = item.get("remetente")
        mensagem = item.get("mensagem")
        if mensagem:
            add_message(mensagem, is_me=remetente == "usuario")

    def perfil_eh_mock():
        return (
            perfil.get("tipo") == "mock"
            or perfil.get("origem") == "mock"
            or str(perfil.get("id", "")).startswith(("user_", "custom_"))
        )

    def resposta_mock(texto_usuario):
        respostas = perfil.get("respostas") or [
            "Gostei desse comeco. Me conta mais sobre voce.",
            "Esse assunto tem cara de render uma conversa longa.",
            "Curti a pergunta. Quero saber como isso aparece no seu dia a dia.",
        ]
        indice = state["respostas_enviadas"] % len(respostas)
        state["respostas_enviadas"] += 1
        texto_usuario = texto_usuario.lower()

        if "oi" in texto_usuario or "ola" in texto_usuario:
            return f"Oi! Eu sou {perfil['nome']}. Bom te ver por aqui."

        return respostas[indice]

    async def load_saved_messages():
        state["carregando"] = True
        historico = await carregar_historico_match(match_id_ativo, usuario_logado)
        messages_view.controls.clear()

        if historico:
            for item in historico:
                append_message(item)
            set_status("Conversa carregada do banco.", CORAL)
        elif perfil_eh_mock():
            saudacao = f"Oi, eu sou {perfil['nome']}. Vi nosso match e fiquei curiosa para conversar."
            add_message(saudacao, is_me=False)
            await salvar_mensagem_match(match_id_ativo, saudacao, "match", usuario_logado)
            set_status("Conversa iniciada e salva no banco.", CORAL)
        else:
            set_status("Match confirmado. Envie a primeira mensagem quando quiser.", CORAL)

        state["carregando"] = False

    async def enviar_mensagem_async(texto_usuario):
        resultado = await salvar_mensagem_match(
            match_id_ativo,
            texto_usuario,
            "usuario",
            usuario_logado,
        )
        if not resultado.get("sucesso"):
            set_status(resultado.get("mensagem", "Falha ao salvar mensagem."), ft.Colors.RED_500)
            return

        if perfil_eh_mock():
            resposta = resposta_mock(texto_usuario)
            add_message(resposta, is_me=False)
            resposta_salva = await salvar_mensagem_match(
                match_id_ativo,
                resposta,
                "match",
                usuario_logado,
            )

            if resposta_salva.get("sucesso"):
                set_status("Mensagem salva no banco.", CORAL)
            else:
                set_status(resposta_salva.get("mensagem", "Falha ao salvar resposta."), ft.Colors.RED_500)
            return

        set_status("Mensagem salva no banco.", CORAL)

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
            asyncio.get_running_loop().create_task(enviar_mensagem_async(texto_usuario))

    def sugestao_chip(sugestao):
        texto = sugestao.get("texto", "") if isinstance(sugestao, dict) else str(sugestao)
        return ft.Container(
            content=ft.Text(texto, size=12, color=TEXT_MAIN),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=12,
            padding=10,
            on_click=lambda _: preencher_sugestao(texto),
        )

    def preencher_sugestao(texto):
        field.value = texto
        field.focus()
        page.update()

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

    if hasattr(page, "run_task"):
        page.run_task(load_saved_messages)
    else:
        asyncio.get_running_loop().create_task(load_saved_messages())

    profile_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Image(src=perfil["imagem"], fit=ft.BoxFit.COVER, width=52, height=52),
                    width=52,
                    height=52,
                    border_radius=26,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                ft.Column(
                    controls=[
                        ft.Text(perfil["nome"], size=17, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text(
                            "Conversa liberada",
                            size=12,
                            color=TEXT_MUTED,
                        ),
                    ],
                    expand=True,
                    spacing=0,
                ),
                ft.TextButton(
                    content="Perfil",
                    icon=ft.Icons.PERSON,
                    on_click=lambda _: (
                        setattr(page, "match_result", perfil_para_payload(perfil)),
                        page.go("/match"),
                    ),
                    style=ft.ButtonStyle(color=CORAL),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        padding=ft.Padding(12, 10, 12, 10),
    )

    sugestoes_area = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Sugestoes para comecar", size=12, color=TEXT_MUTED),
                ft.Row(
                    controls=[sugestao_chip(s) for s in sugestoes],
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                ),
            ],
            spacing=8,
        ),
        visible=bool(sugestoes),
        bgcolor=BG_MUTED,
        padding=ft.Padding(12, 10, 12, 8),
    )

    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_button]),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(top=ft.BorderSide(1, BORDER)),
        padding=ft.Padding(10, 8, 10, 8),
    )

    content = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            profile_bar,
            sugestoes_area,
            ft.Container(content=status_text, padding=ft.Padding(16, 6, 16, 6), bgcolor=BG_MAIN),
            ft.Container(content=messages_view, expand=True, bgcolor=BG_MUTED),
            sender_container,
        ],
    )

    return authenticated_view(
        page,
        "/chatmatch",
        "Conversa",
        content,
        subtitle="Historico salvo por match confirmado.",
        show_back=True,
    )

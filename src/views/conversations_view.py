import asyncio

import flet as ft

from src.services.api_client import listar_matches
from src.views.app_layout import (
    BG_MUTED,
    BORDER,
    CORAL,
    PINK,
    TEXT_MAIN,
    TEXT_MUTED,
    authenticated_view,
)
from src.views.match_view import montar_perfil_match, perfil_para_payload


def conversationsView(page: ft.Page) -> ft.View:
    usuario_logado = getattr(page, "usuario_logado", None)
    state = {"matches": [], "carregando": True}
    list_area = ft.Container(expand=True)
    status_text = ft.Text("Carregando conversas...", size=12, color=TEXT_MUTED)

    def abrir_conversa(match_salvo):
        perfil = montar_perfil_match(match_salvo)
        page.active_match_id = perfil["id"]
        page.match_result = perfil_para_payload(perfil)
        page.active_match_payload = perfil_para_payload(perfil)
        page.match_sugestoes = perfil.get("sugestoes_inicio", [])
        page.go("/chatmatch")

    def render_item(match_salvo):
        perfil = montar_perfil_match(match_salvo)
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src=perfil["imagem"],
                            fit=ft.BoxFit.COVER,
                            width=58,
                            height=58,
                        ),
                        width=58,
                        height=58,
                        border_radius=29,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(perfil["nome"], size=16, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                            ft.Text(
                                perfil.get("descricao", "")[:96],
                                size=12,
                                color=TEXT_MUTED,
                            ),
                        ],
                        expand=True,
                        spacing=3,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                        icon_color=PINK,
                        tooltip="Abrir conversa",
                        on_click=lambda _, match=match_salvo: abrir_conversa(match),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=16,
            padding=12,
            on_click=lambda _, match=match_salvo: abrir_conversa(match),
        )

    def render():
        if state["carregando"]:
            list_area.content = ft.Container(
                content=ft.ProgressRing(color=CORAL),
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        elif not state["matches"]:
            list_area.content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=54, color=PINK),
                        ft.Text(
                            "Suas conversas confirmadas aparecem aqui.",
                            color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.FilledButton(
                            content="Descobrir perfis",
                            icon=ft.Icons.FAVORITE,
                            on_click=lambda _: page.go("/match"),
                            style=ft.ButtonStyle(bgcolor=CORAL, color=ft.Colors.WHITE),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=14,
                ),
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        else:
            list_area.content = ft.ListView(
                controls=[render_item(match) for match in state["matches"]],
                expand=True,
                spacing=10,
                padding=ft.Padding(16, 12, 16, 16),
            )

        try:
            list_area.update()
        except (AssertionError, RuntimeError):
            pass

    async def carregar():
        state["carregando"] = True
        render()
        state["matches"] = await listar_matches(usuario_logado)
        state["carregando"] = False
        status_text.value = (
            "Toque em uma conversa para continuar."
            if state["matches"]
            else "Nenhum match confirmado ainda."
        )
        status_text.color = CORAL if state["matches"] else TEXT_MUTED
        render()
        page.update()

    if hasattr(page, "run_task"):
        page.run_task(carregar)
    else:
        asyncio.get_running_loop().create_task(carregar())

    content = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            ft.Container(content=status_text, padding=ft.Padding(16, 10, 16, 4), bgcolor=ft.Colors.WHITE),
            ft.Container(content=list_area, expand=True, bgcolor=BG_MUTED),
        ],
    )

    return authenticated_view(
        page,
        "/conversas",
        "Conversas",
        content,
        subtitle="Somente matches confirmados liberam chat.",
    )

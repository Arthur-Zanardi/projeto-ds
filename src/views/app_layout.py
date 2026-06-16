import flet as ft


CORAL = "#FF7F50"
PINK = "#D63384"
BG_MAIN = "#FAFAFA"
BG_MUTED = "#F3F4F6"
TEXT_MAIN = "#111827"
TEXT_MUTED = "#6B7280"
BORDER = "#E5E7EB"

NAV_ROUTES = ["/chat", "/match", "/conversas", "/profile"]


def logout(page: ft.Page):
    for attr in (
        "usuario_logado",
        "match_result",
        "match_deck",
        "active_match_id",
        "active_match_payload",
        "match_sugestoes",
    ):
        if hasattr(page, attr):
            setattr(page, attr, None)

    page.views.clear()
    page.go("/login")


def selected_index_for(route: str):
    if route == "/chatmatch":
        return 2

    try:
        return NAV_ROUTES.index(route)
    except ValueError:
        return 0


def navigation_bar(page: ft.Page, selected_route: str):
    def on_change(event):
        indice = event.control.selected_index
        page.go(NAV_ROUTES[indice])

    return ft.NavigationBar(
        selected_index=selected_index_for(selected_route),
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.AUTO_AWESOME_OUTLINED,
                selected_icon=ft.Icons.AUTO_AWESOME,
                label="Entrevista",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.FAVORITE_BORDER,
                selected_icon=ft.Icons.FAVORITE,
                label="Descobrir",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                selected_icon=ft.Icons.CHAT_BUBBLE,
                label="Conversas",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PERSON_OUTLINE,
                selected_icon=ft.Icons.PERSON,
                label="Perfil",
            ),
        ],
        bgcolor=ft.Colors.WHITE,
        indicator_color="#FFE4EC",
        on_change=on_change,
    )


def app_header(
    page: ft.Page,
    title: str,
    subtitle: str | None = None,
    show_back: bool = False,
):
    usuario = getattr(page, "usuario_logado", {}) or {}

    leading = (
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=TEXT_MAIN,
            tooltip="Voltar",
            on_click=lambda _: page.go("/conversas"),
        )
        if show_back
        else ft.Container(
            content=ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.WHITE, size=20),
            width=40,
            height=40,
            border_radius=12,
            gradient=ft.LinearGradient(colors=[CORAL, PINK]),
            alignment=ft.Alignment(0, 0),
        )
    )

    title_controls = [
        ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
    ]
    if subtitle:
        title_controls.append(ft.Text(subtitle, size=12, color=TEXT_MUTED))

    return ft.Container(
        content=ft.Row(
            controls=[
                leading,
                ft.Column(title_controls, spacing=2, expand=True),
                ft.IconButton(
                    icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                    icon_color=PINK,
                    tooltip="Conversas",
                    on_click=lambda _: page.go("/conversas"),
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    icon_color=TEXT_MUTED,
                    tooltip=f"Sair de {usuario.get('nome', 'conta')}",
                    on_click=lambda _: logout(page),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG_MAIN,
        padding=ft.Padding(16, 12, 12, 8),
    )


def authenticated_view(
    page: ft.Page,
    route: str,
    title: str,
    content: ft.Control,
    subtitle: str | None = None,
    show_back: bool = False,
    bgcolor: str = BG_MAIN,
):
    return ft.View(
        route=route,
        bgcolor=bgcolor,
        padding=0,
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    app_header(page, title, subtitle, show_back=show_back),
                    ft.Container(content=content, expand=True),
                    navigation_bar(page, route),
                ],
            )
        ],
    )

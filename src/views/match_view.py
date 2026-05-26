import flet as ft


PERFIS_MOCK = {
    "user_maria": {
        "nome": "Maria",
        "idade": 22,
        "localizacao": "Recife, PE",
        "cargo": "Estudante de Tecnologia",
        "tracos": ["Comunicativa", "Criativa", "Aventureira"],
        "imagem": "https://images.unsplash.com/photo-1748344386932-f0b9c7b925e6?w=500&q=80",
    },
    "user_carmen": {
        "nome": "Carmen",
        "idade": 24,
        "localizacao": "Olinda, PE",
        "cargo": "Designer",
        "tracos": ["Carinhosa", "Tranquila", "Caseira"],
        "imagem": "https://images.unsplash.com/photo-1748344386932-f0b9c7b925e6?w=500&q=80",
    },
}

PERFIL_PADRAO = {
    "nome": "Beatriz Lima",
    "idade": 19,
    "localizacao": "Recife, PE",
    "cargo": "Product Designer",
    "tracos": ["Empatica", "Criativa", "Aventureira"],
    "imagem": "https://images.unsplash.com/photo-1748344386932-f0b9c7b925e6?w=500&q=80",
}


def montar_perfil_match(match_result):
    if not match_result:
        return PERFIL_PADRAO.copy()

    perfil = {
        **PERFIL_PADRAO,
        **PERFIS_MOCK.get(match_result.get("id"), {}),
    }
    perfil["nome"] = match_result.get("nome") or perfil["nome"]
    perfil["afinidade"] = match_result.get("afinidade")
    perfil["dimensoes_comparadas"] = match_result.get("dimensoes_comparadas")
    return perfil


def matchView(page):
    match = montar_perfil_match(getattr(page, "match_result", None))

    def go_back(e):
        page.go("/chat")

    def goto_chatmatch_view(e):
        page.go("/chatmatch")

    badge_controls = [
        ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.PINK_500, size=16)
    ]
    if match.get("afinidade"):
        badge_controls.append(
            ft.Text(match["afinidade"], size=12, color=ft.Colors.PINK_500)
        )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.BLACK_87,
                    on_click=go_back,
                ),
                ft.Text(
                    "Seu Match",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLACK_87,
                ),
                ft.Container(width=40),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=15,
        bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.WHITE),
        blur=ft.Blur(10, 10),
    )

    image_section = ft.Stack(
        controls=[
            ft.Image(
                src=match["imagem"],
                fit=ft.BoxFit.COVER,
                height=350,
                width=float("inf"),
            ),
            ft.Container(
                content=ft.Row(
                    controls=badge_controls,
                    spacing=4,
                ),
                top=15,
                right=15,
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.WHITE),
                padding=15,
                border_radius=20,
            ),
        ]
    )

    traits_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(trait, size=12, color=ft.Colors.BLACK_87),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.PINK_100),
                border_radius=15,
                padding=10,
            )
            for trait in match["tracos"]
        ],
        wrap=True,
    )

    action_buttons = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=ft.Colors.GREY_600,
                icon_size=30,
                bgcolor=ft.Colors.WHITE,
            ),
            ft.IconButton(
                icon=ft.Icons.FAVORITE,
                icon_color=ft.Colors.WHITE,
                icon_size=40,
                bgcolor=ft.Colors.PINK_400,
            ),
            ft.IconButton(
                icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                icon_color=ft.Colors.PINK_500,
                icon_size=30,
                bgcolor=ft.Colors.WHITE,
                on_click=goto_chatmatch_view,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
    )

    main_card = ft.Container(
        content=ft.Column(
            [
                image_section,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"{match['nome']}, {match['idade']}",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLACK_87,
                            ),
                            ft.Text(
                                f"{match['localizacao']} - {match['cargo']}",
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Divider(color=ft.Colors.TRANSPARENT, height=10),
                            ft.Text(
                                "Personality",
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLACK_87,
                            ),
                            traits_row,
                        ]
                    ),
                    padding=20,
                ),
            ]
        ),
        bgcolor=ft.Colors.WHITE,
        border_radius=20,
        margin=10,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.Colors.BLACK_12,
        ),
    )

    conteudo_perfil = ft.Column(
        controls=[
            header,
            main_card,
            action_buttons,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.View(
        route="/match",
        controls=[
            conteudo_perfil,
        ],
        bgcolor=ft.Colors.PINK_50,
    )

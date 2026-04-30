import flet as ft
from src.services.api_client import dar_match

def matchView(page):
    async def go_back():
        page.views.pop()
        await page.push_route("/")
    
    match = {
        "nome": "Beatriz Lima",
        "idade": 19,
        "localização": "Recife, PE",
        "cargo": "Product Designer",
        "traços": ["Empática", "Criativa", "Aventureira"]
    }
    
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.BLACK_87, on_click=go_back),
                ft.Text("Seu Match", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87),
                ft.Container(width=40) 
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        padding=15,
        bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.WHITE),
        blur=ft.Blur(10, 10) 
    )

    image_section = ft.Stack(
        controls=[
            ft.Image(
                src="https://images.unsplash.com/photo-1748344386932-f0b9c7b925e6?w=500&q=80",
                fit=ft.BoxFit.COVER,
                height=350,
                width=float("inf"),
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.PINK_500, size=16),
                    
                ]),
                top=15,
                right=15,
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.WHITE),
                padding=15,
                border_radius=20,
            )
        ]
    )

    traits_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(trait, size=12, color=ft.Colors.BLACK_87),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.PINK_100), 
                border_radius=15,
                padding=10
            ) for trait in match["traços"]
        ],
        wrap=True 
    )

    action_buttons = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.CLOSE, icon_color=ft.Colors.GREY_600, icon_size=30, bgcolor=ft.Colors.WHITE),
            ft.IconButton(icon=ft.Icons.FAVORITE, icon_color=ft.Colors.WHITE, icon_size=40, bgcolor=ft.Colors.PINK_400),
            ft.IconButton(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, icon_color=ft.Colors.PINK_500, icon_size=30, bgcolor=ft.Colors.WHITE),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20
    )

    main_card = ft.Container(
        content=ft.Column([
            image_section,
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{match['nome']}, {match['idade']}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87),
                    ft.Text(f"{match['localização']} • {match['cargo']}", color=ft.Colors.GREY_700),
                    ft.Divider(color=ft.Colors.TRANSPARENT, height=10),
                    ft.Text("Personality", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87),
                    traits_row,
                ]),
                padding=20
            )
        ]),
        bgcolor=ft.Colors.WHITE,
        border_radius=20, 
        margin=10,         
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.BLACK_12)
    )

    conteudo_perfil = ft.Column(
        controls=[
            header,
            main_card,
            action_buttons
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    # --- Saída de View ---
    return ft.View(
        route="/match",
        controls=[
            conteudo_perfil,
        ],
        bgcolor=ft.Colors.PINK_50,
    )
import flet as ft

def profileView(page: ft.Page) -> ft.View:
    CORAL = "#FF7F50"
    PINK = "#FF69B4"
    BG_MAIN = "#FAFAFA"
    BG_SECONDARY = "#F3F4F6"
    TEXT_MAIN = "#111827"
    TEXT_MUTED = "#6B7280"
    BORDER_COLOR = "#E5E7EB"
    GLASS_BG = "#FFFFFF" 

    state = {
        "selected_tags": ["Alma Criativa", "Empático"],
        "has_photo": True
    }

    personality_tags = [
        "Alma Criativa", "Pensador Profundo", "Aventureiro",
        "Empático", "Ambicioso", "Bem-humorado"
    ]

    async def go_back(e):
        page.views.pop()
        page.go(page.views[-1].route)

    async def on_complete(e):
        page.views.pop()
        await page.push_route("/match") 

    header = ft.Container(
        content=ft.Row([
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=TEXT_MAIN,
                on_click=go_back
            ),
            ft.Column([
                ft.Text("Monte seu perfil", size=18, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ft.Text("Deixe a IA personalizar sua presença", size=12, color=TEXT_MUTED)
            ], spacing=2)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(top=10, bottom=10),
        bgcolor=BG_MAIN,
    )

    photo_avatar = ft.Container(
        width=128,
        height=128,
        border_radius=64,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        alignment=ft.Alignment(0.0, 0.0),
    )

    def update_photo_ui():
        if state["has_photo"]:
            photo_avatar.border = ft.border.all(4, CORAL)
            photo_avatar.bgcolor = ft.Colors.TRANSPARENT
            photo_avatar.content = ft.Image(
                src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop",
                fit="cover",
                width=128,
                height=128,
            )
        else:
            photo_avatar.border = ft.border.all(4, BORDER_COLOR)
            photo_avatar.bgcolor = BG_SECONDARY
            photo_avatar.content = ft.Column([
                ft.Icon(ft.Icons.CAMERA_ALT, size=32, color=TEXT_MUTED),
                ft.Text("Adicionar", size=12, color=TEXT_MUTED)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
        
        page.update()

    def toggle_photo(e):
        state["has_photo"] = not state["has_photo"]
        update_photo_ui()

    photo_edit_btn = ft.Container(
        content=ft.Icon(ft.Icons.CAMERA_ALT, size=16, color=ft.Colors.WHITE),
        width=36,
        height=36,
        border_radius=18,
        gradient=ft.LinearGradient(colors=[CORAL, PINK]),
        alignment=ft.Alignment(0.0, 0.0),
        on_click=toggle_photo,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.BLACK12)
    )

    photo_section = ft.Column([
        ft.Text("Foto de perfil", size=14, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
        ft.Container(
            content=ft.Column([
                ft.Stack([
                    photo_avatar,
                    ft.Container(
                        content=photo_edit_btn,
                        alignment=ft.Alignment(1, 1),
                        width=132,
                        height=132
                    )
                ]),
                ft.Text("Escolha uma foto que represente bem quem você é", size=12, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            alignment=ft.Alignment(0.0, 0.0)
        )
    ], spacing=12, margin=ft.margin.only(bottom=24))

    update_photo_ui()


    bio_section = ft.Column([
        ft.Row([
            ft.Text("Bio gerada pela IA", size=14, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=12, color=CORAL),
                    ft.Text("IA", size=10, weight=ft.FontWeight.BOLD, color=CORAL)
                ], spacing=4),
                bgcolor="#FFE4E1", 
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=12
            )
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        
        ft.Container(
            content=ft.Column([
                ft.TextField(
                    value="Alma criativa apaixonada por fotografia e conversas que duram até tarde. Acredito que as melhores conexões acontecem quando duas mentes curiosas se encontram. Procuro alguém que aprecie tanto aventuras espontâneas quanto noites aconchegantes em casa.",
                    multiline=True,
                    min_lines=4,
                    max_lines=5,
                    border_color=ft.Colors.TRANSPARENT,
                    bgcolor=ft.Colors.TRANSPARENT,
                    text_size=14,
                    color=TEXT_MAIN,
                    content_padding=0
                ),
                ft.Row([
                    ft.TextButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.AUTO_AWESOME, size=14, color=CORAL),
                            ft.Text("Regenerar", size=12, color=CORAL, weight=ft.FontWeight.BOLD)
                        ], spacing=4),
                        style=ft.ButtonStyle(overlay_color=ft.Colors.TRANSPARENT)
                    )
                ], alignment=ft.MainAxisAlignment.END)
            ]),
            bgcolor=BG_SECONDARY,
            border=ft.border.all(1, BORDER_COLOR),
            border_radius=16,
            padding=16
        )
    ], spacing=12, margin=ft.margin.only(bottom=24))


    tags_container = ft.Row(wrap=True, spacing=8, run_spacing=8)

    def render_tags():
        tags_container.controls.clear()
        for tag in personality_tags:
            is_selected = tag in state["selected_tags"]
            
            bg_color = ft.Colors.TRANSPARENT if not is_selected else None
            gradient = ft.LinearGradient(colors=[CORAL, PINK]) if is_selected else None
            text_color = ft.Colors.WHITE if is_selected else TEXT_MAIN
            border = None if is_selected else ft.border.all(1, BORDER_COLOR)
            
            row_controls = [ft.Text(tag, size=13, color=text_color, weight=ft.FontWeight.W_500)]
            if is_selected:
                row_controls.append(ft.Icon(ft.Icons.CHECK, size=14, color=ft.Colors.WHITE))
            
            tag_btn = ft.Container(
                content=ft.Row(row_controls, spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=bg_color if not gradient else None,
                gradient=gradient,
                border=border,
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                on_click=lambda e, t=tag: toggle_tag(t)
            )
            tags_container.controls.append(tag_btn)

    def toggle_tag(tag_name):
        if tag_name in state["selected_tags"]:
            state["selected_tags"].remove(tag_name)
        else:
            state["selected_tags"].append(tag_name)
        render_tags()
        page.update()

    render_tags()

    tags_section = ft.Column([
        ft.Row([
            ft.Text("Tags de personalidade", size=14, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
            ft.Text("Toque para selecionar", size=11, color=TEXT_MUTED)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        tags_container
    ], spacing=12, margin=ft.margin.only(bottom=24))


    insight_section = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, size=20, color=CORAL),
                ft.Text("Insight de compatibilidade", size=14, weight=ft.FontWeight.W_600, color=TEXT_MAIN)
            ], spacing=8),
            ft.Text(
                "Com base na sua entrevista, você valoriza conexão intelectual e profundidade emocional. "
                "Seu match ideal provavelmente compartilha seus interesses criativos e aprecia conversas verdadeiras.",
                size=13,
                color=TEXT_MUTED,
            )
        ], spacing=12),
        bgcolor=GLASS_BG,
        border=ft.border.all(1, BORDER_COLOR),
        border_radius=16,
        padding=16,
        margin=ft.margin.only(bottom=40), 
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.Colors.BLACK12)
    )

    cta_button = ft.Container(
        content=ft.Text("Começar a encontrar matches", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=16),
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1.0, 0.0),
            end=ft.Alignment(1.0, 0.0),
            colors=[CORAL, PINK]
        ),
        height=56,
        border_radius=16,
        alignment=ft.Alignment(0.0, 0.0),
        on_click=on_complete,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="#4DFF7F50") 
    )

    return ft.View(
        route="/profile",
        bgcolor=BG_MAIN,
        padding=0, 
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                content=ft.Column([
                    header,
                    photo_section,
                    bio_section,
                    tags_section,
                    insight_section,
                    cta_button
                ]),
                padding=20 
            )
        ]
    )
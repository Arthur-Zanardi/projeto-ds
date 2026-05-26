import flet as ft


def matchChatView(page, match_name="Seu Match", match_id=123):
    def goto_profile_screen(e):
        page.go(f"/profile/{match_id}")

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

    def send_clicked(e):
        texto_usuario = field.value.strip()
        if not texto_usuario:
            return

        add_message(texto_usuario, is_me=True)

        field.value = ""
        field.focus()
        page.update()

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

    send_buttom = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SEND,
            icon_color=ft.Colors.WHITE,
            on_click=send_clicked,
        ),
        gradient=new_gradient,
        shape=ft.BoxShape.CIRCLE,
    )

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(
                    f"Chat com {match_name}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLACK_87,
                ),
                ft.TextButton(
                    content="Ver Perfil",
                    icon=ft.Icons.PERSON,
                    on_click=goto_profile_screen,
                    style=ft.ButtonStyle(color="#d63384"),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.Padding.only(top=10, bottom=10, left=20, right=10),
    )

    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_buttom]),
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
        route="/chatmatch",
        controls=[column],
        bgcolor=ft.Colors.PINK_50,
    )

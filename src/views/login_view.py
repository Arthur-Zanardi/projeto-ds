import flet as ft


def login_button_style(fg_color, bg_color):
    return ft.ButtonStyle(
        color= fg_color,
        bgcolor= bg_color,
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=24,
        elevation={
            ft.ControlState.DEFAULT: 0,
            ft.ControlState.HOVERED: 5,
            ft.ControlState.PRESSED: 10,
        },
        animation_duration=500,
    )


def loginView():
    fg_color = "#232d3b"
    bg_color = "#fffbfc"

    # --- Instância dos botões ---
    google_login = ft.Button(
        content=ft.Text("Continue with Google",size=14),
        icon=ft.Image(src="assets/icons/google.svg",width=24,height=24),
        style=login_button_style(fg_color, bg_color)
    )

    facebook_login = ft.Button(
        content=ft.Text("Continue with Facebook",size=14),
        icon=ft.Image(src="assets/icons/facebook.svg",width=24,height=24),
        style=login_button_style(fg_color, bg_color)
    )

    apple_login = ft.Button(
        content=ft.Text("Continue with Apple",size=14),
        icon=ft.Image(src="assets/icons/apple.svg",width=24,height=24),
        style=login_button_style(fg_color, bg_color)
    )

    # --- Saída de View ---
    return ft.View(
        route="/login",
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            google_login,
            facebook_login,
            apple_login,
        ],
    )
import flet as ft
from dataclasses import field

# Classe padrão para os botões grandes
@ft.control
class DefaultButton(ft.Button):
    expand: int = 1
    style: ft.ButtonStyle = field(
        default_factory=lambda: ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=24,
        )
    )

@ft.control
class LoginButton(DefaultButton):
    bgcolor:    ft.Colors = "#fffbfc"
    color:      ft.Colors = "#232d3b"

@ft.control
class SignUpButton(DefaultButton):
    bgcolor:    "#ff6b6b"
    color:      "#ffffff"

def main(page: ft.Page):
    page.fonts = {"Google Sans Flex": "assets/fonts/GoogleSansFlex.ttf"}

    # --- Instância dos botões ---
    google_login = LoginButton(content=ft.Text("Continue with Google",size=14), icon=ft.Image(src="assets/icons/google.svg",width=24,height=24))
    facebook_login = LoginButton(content=ft.Text("Continue with Facebook",size=14), icon=ft.Image(src="assets/icons/facebook.svg",width=24,height=24))
    apple_login = LoginButton(content=ft.Text("Continue with Apple",size=14), icon=ft.Image(src="assets/icons/apple.svg",width=24,height=24))

    # --- Organização da tela em uma única coluna ---
    column = ft.Column(
        # width=412,
        # height=915,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
        controls=[
            google_login,
            facebook_login,
            apple_login,
        ],
    )

    # --- Atributos da tela do app ---
    page.title = "MatchAI"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.height=915
    page.width=412
    page.theme = ft.Theme(font_family="Google Sans Flex")

    page.add(column)

if __name__ == "__main__":
    ft.run(main)
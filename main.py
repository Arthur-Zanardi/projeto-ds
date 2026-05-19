import asyncio
import flet as ft

from src.views.login_view import loginView
from src.views.chat_view import chatView
from src.views.match_view import matchView
from src.views.tela_perfil import profileView

async def main(page: ft.Page):
    page.fonts = {"Google Sans Flex": "assets/fonts/GoogleSansFlex.ttf"}

    page.title = "Match.AI"
    page.height = 915
    page.width = 412
    page.theme = ft.Theme(font_family="Google Sans Flex")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

    def route_change(e=None):
        print(f"Navegando para: {page.route}")
        page.views.clear()

        if page.route == "/" or page.route == "/login":
            page.views.append(loginView(page))

        elif page.route == "/match":
            page.views.append(matchView(page))

        elif page.route == "/profile":
            page.views.append(profileView(page))

        elif page.route == "/chat":
            page.views.append(matchView(page))
            page.views.append(chatView(page))
        

        page.update()

    async def view_pop(e):
        if e.view is not None:
            print("View pop executado em:", e.view)
            page.views.remove(e.view)
            top_view = page.views[-1]
            await page.go_async(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    if page.route == "" or page.route is None:
        page.route = "/"
        
    route_change()


if __name__ == "__main__":
    ft.app(target=main)
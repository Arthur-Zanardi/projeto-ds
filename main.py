import asyncio
import flet as ft

from src.views.login_view import loginView
from src.views.chat_view import chatView
from src.views.match_view import matchView


async def main(page: ft.Page):
    page.fonts = {"Google Sans Flex": "assets/fonts/GoogleSansFlex.ttf"}

    page.title = "Match.AI"
    page.height = 915
    page.width = 412
    page.theme = ft.Theme(font_family="Google Sans Flex")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

    async def open_login(e=None):
        await page.push_route("/login")

    async def open_chat(e=None):
        await page.push_route("/chat")

    async def open_match_screen(e=None):
        await page.push_route("/match")

    def route_change(e=None):
        print(f"Changed route to {page.route}")

        page.views.clear()

        page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.Text("Tela Base", size=32),
                    ft.Text("Ambiente para testes", size=26),
                    ft.Button(content=ft.Text("Login"), on_click=open_login),
                    ft.Button(content=ft.Text("Chat"), on_click=open_chat),
                    ft.Button(content=ft.Text("Match"), on_click=open_match_screen),
                ],
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        if page.route == "/login":
            page.views.append(loginView(page))

        elif page.route == "/chat":
            page.views.append(chatView(page))

        elif page.route == "/match":
            page.views.append(matchView(page))

        page.update()

    async def view_pop(e):
        if e.view is not None:
            print("View pop:", e.view)
            page.views.remove(e.view)

            top_view = page.views[-1]
            await page.go_async(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    route_change()


if __name__ == "__main__":
    ft.app(target=main)
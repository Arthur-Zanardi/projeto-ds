import asyncio
import flet as ft
from src.views.login_view import loginView
from src.views.chat_view import chatView

async def main(page: ft.Page):
    page.fonts = {"Google Sans Flex": "assets/fonts/GoogleSansFlex.ttf"}

    page.title = "Match.AI"
    page.height=915
    page.width=412
    page.theme = ft.Theme(font_family="Google Sans Flex")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    async def open_login():
        await page.push_route("/login")

    async def open_chat():
        await page.push_route("/chat")

    def route_change():
        print(f"Changed route to {page.route}")
        page.views.clear()
        page.views.append(
            # Página Base

            ft.View(
                route="/",
                controls=[
                    ft.Text("Tela Base", size=32),
                    ft.Button(content="Login", on_click=open_login),
                    ft.Button(content="Chat", on_click=open_chat),
                ],
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        if page.route == "/login":
            page.views.append(loginView())

        if page.route == "/chat":
            page.views.append(chatView())

    async def view_pop(view):
        print(top_view.route)
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)


    page.on_route_change = route_change
    page.on_view_pop = view_pop

    route_change()

if __name__ == "__main__":
    ft.run(main)
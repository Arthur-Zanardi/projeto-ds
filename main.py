import logging
import os

import flet as ft

from src.services.profile_images import MAX_PROFILE_IMAGE_BYTES
from src.views.chat_match_view import matchChatView
from src.views.chat_view import chatView
from src.views.conversations_view import conversationsView
from src.views.login_view import loginView
from src.views.match_view import matchView
from src.views.tela_perfil import profileView

logger = logging.getLogger(__name__)


async def main(page: ft.Page):
    page.fonts = {"Google Sans Flex": "assets/fonts/GoogleSansFlex.ttf"}

    page.title = "Match.AI"
    page.theme = ft.Theme(font_family="Google Sans Flex")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

    def usuario_autenticado():
        return bool(getattr(page, "usuario_logado", None))

    def mostrar_login():
        page.views.append(loginView(page))

    def route_change(_=None):
        logger.info("Navegando para: %s", page.route)
        page.views.clear()

        if page.route in ("/", "/login", "", None):
            mostrar_login()

        elif page.route == "/match":
            if usuario_autenticado():
                page.views.append(matchView(page))
            else:
                page.route = "/login"
                mostrar_login()

        elif page.route == "/profile":
            if usuario_autenticado():
                page.views.append(profileView(page))
            else:
                page.route = "/login"
                mostrar_login()

        elif page.route.startswith("/profile/"):
            if usuario_autenticado():
                page.views.append(profileView(page))
            else:
                page.route = "/login"
                mostrar_login()

        elif page.route == "/chat":
            if usuario_autenticado():
                page.views.append(chatView(page))
            else:
                page.route = "/login"
                mostrar_login()

        elif page.route == "/conversas":
            if usuario_autenticado():
                page.views.append(conversationsView(page))
            else:
                page.route = "/login"
                mostrar_login()

        elif page.route == "/chatmatch":
            if usuario_autenticado():
                page.views.append(matchChatView(page))
            else:
                page.route = "/login"
                mostrar_login()
        else:
            page.route = "/login"
            mostrar_login()

        page.update()

    def view_pop(e):
        if e.view is not None and e.view in page.views:
            logger.debug("View pop executado em: %s", e.view)
            page.views.remove(e.view)

        top_view = page.views[-1] if page.views else None
        page.go(top_view.route if top_view else "/login")

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    if page.route == "" or page.route is None:
        page.route = "/"

    route_change()


if __name__ == "__main__":
    os.environ.setdefault("FLET_MAX_UPLOAD_SIZE", str(MAX_PROFILE_IMAGE_BYTES))
    ft.app(target=main, upload_dir="assets")

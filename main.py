from __future__ import annotations

import asyncio
import os
from typing import Any

import flet as ft
import requests

from src.schema.schema_vetores import (
    GENDER_LABELS,
    GROUP_LABELS,
    INTERESTED_IN_LABELS,
    INTEREST_LABELS,
    PHYSICAL_LABELS,
    PHYSICAL_VECTOR_SCHEMA,
    VALUE_LABELS,
    default_profile_vectors,
)


API_BASE = os.getenv("MATCHAI_API_URL", "http://127.0.0.1:8000")
API_DOWN_MESSAGE = (
    "A API local nÃ£o estÃ¡ rodando em 127.0.0.1:8000. "
    "Abra o app pelo launcher: python scripts/run_matchai.py "
    "ou use o start_matchai.bat."
)

LIGHT = {
    "bg": "#FFF7FA",
    "surface": "#FFFFFF",
    "surface_alt": "#FFE7EF",
    "primary": "#D7264D",
    "primary_soft": "#FF6B8A",
    "accent": "#FFB3C7",
    "text": "#2B1B22",
    "muted": "#7C5964",
    "border": "#FFD0DD",
}

DARK = {
    "bg": "#211018",
    "surface": "#2E1621",
    "surface_alt": "#3B1D2A",
    "primary": "#FF6B8A",
    "primary_soft": "#FF8FA5",
    "accent": "#5A2436",
    "text": "#FFF4F7",
    "muted": "#DDB6C3",
    "border": "#6F2C42",
}

INTEREST_KEYS = [
    "animes",
    "musica",
    "filmes",
    "series",
    "livros_ficcao",
    "tecnologia",
    "academia",
    "futebol",
    "videogames",
    "astronomia",
]

FILTER_KEYS = [
    "valores.espectro_politico",
    "valores.conservadorismo",
    "valores.religiosidade",
    "valores.gosto_festas",
]

PHYSICAL_CATEGORIES = [
    ("Cor dos olhos", ["olhos_pretos", "olhos_castanhos", "olhos_mel_avela", "olhos_verdes", "olhos_azuis", "olhos_cinzas"]),
    ("Cor do cabelo", ["cabelo_preto", "cabelo_castanho", "cabelo_loiro", "cabelo_ruivo", "cabelo_colorido"]),
    ("Formato do cabelo", ["cabelo_liso", "cabelo_ondulado", "cabelo_cacheado", "cabelo_crespo", "cabelo_raspado_careca"]),
    ("Estilo", ["estilo_esportivo", "estilo_elegante", "estilo_alternativo"]),
    ("Altura", ["altura_baixa", "altura_media", "altura_alta"]),
    ("Corpo", ["corpo_magro", "corpo_medio", "corpo_forte"]),
]

PHYSICAL_TOGGLES = ["oculos", "tatuagens_piercings"]


def app_button(
    label: str,
    *,
    icon: Any = None,
    on_click: Any = None,
    palette: dict[str, str] | None = None,
    kind: str = "primary",
    tooltip: str | None = None,
    disabled: bool = False,
) -> ft.Button:
    palette = palette or LIGHT
    styles = {
        "primary": {"bgcolor": palette["primary"], "color": "#FFFFFF"},
        "secondary": {"bgcolor": palette["surface_alt"], "color": palette["primary"]},
        "surface": {"bgcolor": palette["surface"], "color": palette["primary"]},
        "danger": {"bgcolor": palette["primary"], "color": "#FFFFFF"},
    }
    selected = styles.get(kind, styles["primary"])
    return ft.Button(
        label,
        icon=icon,
        on_click=on_click,
        bgcolor=selected["bgcolor"],
        color=selected["color"],
        tooltip=tooltip,
        disabled=disabled,
    )


def primary_button(
    label: str,
    *,
    icon: Any = None,
    on_click: Any = None,
    palette: dict[str, str] | None = None,
    tooltip: str | None = None,
) -> ft.Button:
    return app_button(label, icon=icon, on_click=on_click, palette=palette, tooltip=tooltip)


def secondary_button(
    label: str,
    *,
    icon: Any = None,
    on_click: Any = None,
    palette: dict[str, str] | None = None,
    tooltip: str | None = None,
) -> ft.Button:
    return app_button(
        label,
        icon=icon,
        on_click=on_click,
        palette=palette,
        kind="secondary",
        tooltip=tooltip,
    )


def danger_button(
    label: str,
    *,
    icon: Any = None,
    on_click: Any = None,
    palette: dict[str, str] | None = None,
    tooltip: str | None = None,
) -> ft.Button:
    return app_button(
        label,
        icon=icon,
        on_click=on_click,
        palette=palette,
        kind="danger",
        tooltip=tooltip,
    )


def app_icon_button(
    *,
    icon: Any,
    tooltip: str,
    on_click: Any,
    palette: dict[str, str] | None = None,
) -> ft.IconButton:
    palette = palette or LIGHT
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        icon_color=palette["primary"],
        on_click=on_click,
    )


def main(page: ft.Page):
    state: dict[str, Any] = {
        "token": None,
        "user": None,
        "profile": None,
        "theme_mode": "light",
        "accessibility_mode": False,
        "selected_match": None,
    }

    page.title = "MatchAI"
    page.window_width = 1100
    page.window_height = 760
    page.padding = 0
    photo_picker = ft.FilePicker()
    page.services.append(photo_picker)

    def colors() -> dict[str, str]:
        palette = (DARK if state.get("theme_mode") == "dark" else LIGHT).copy()
        if state.get("accessibility_mode"):
            palette["border"] = "#FFFFFF" if state.get("theme_mode") == "dark" else "#8A102A"
            palette["muted"] = "#FFFFFF" if state.get("theme_mode") == "dark" else "#4A1824"
            palette["surface_alt"] = "#4B2030" if state.get("theme_mode") == "dark" else "#FFE0EA"
        return palette

    def ui_scale() -> float:
        profile = state.get("profile") or {}
        return float(profile.get("ui_font_scale") or profile.get("chat_font_scale") or 1.0)

    def sp(value: int | float) -> int:
        return round(value * ui_scale())

    def apply_theme() -> None:
        palette = colors()
        page.bgcolor = palette["bg"]
        page.theme_mode = (
            ft.ThemeMode.DARK if state.get("theme_mode") == "dark" else ft.ThemeMode.LIGHT
        )

    def snack(message: str) -> None:
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def api_request(
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        auth: bool = True,
        timeout: int = 25,
    ) -> dict[str, Any]:
        headers = {}
        if auth and state.get("token"):
            headers["Authorization"] = f"Bearer {state['token']}"
        try:
            response = requests.request(
                method,
                f"{API_BASE}{path}",
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(API_DOWN_MESSAGE) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError("A API local demorou demais para responder. Tente abrir pelo launcher novamente.") from exc
        try:
            data = response.json()
        except ValueError:
            data = {"detail": response.text}
        if response.status_code >= 400:
            raise RuntimeError(data.get("detail") or data)
        return data

    async def api_request_async(
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        auth: bool = True,
        timeout: int = 25,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(api_request, method, path, json_body, auth, timeout)

    async def run_guarded(
        event: Any,
        action: Any,
        *,
        status: ft.Text | None = None,
        busy_text: str | None = None,
    ) -> Any:
        control = getattr(event, "control", None)
        if control is not None:
            control.disabled = True
        if status is not None and busy_text is not None:
            status.value = busy_text
        page.update()
        try:
            result = action()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as exc:
            if status is not None:
                status.value = str(exc)
            else:
                snack(str(exc))
            return None
        finally:
            if control is not None:
                control.disabled = False
            try:
                page.update()
            except Exception:
                pass

    def save_session(payload: dict[str, Any]) -> None:
        state["token"] = payload["token"]
        state["user"] = payload.get("user")
        try:
            page.client_storage.set("matchai_token", state["token"])
        except Exception:
            pass
        load_profile()
        render_after_login()

    async def save_session_async(payload: dict[str, Any]) -> None:
        state["token"] = payload["token"]
        state["user"] = payload.get("user")
        try:
            page.client_storage.set("matchai_token", state["token"])
        except Exception:
            pass
        data = await api_request_async("GET", "/me")
        state["user"] = data
        state["profile"] = data.get("profile")
        state["theme_mode"] = (state["profile"] or {}).get("theme_mode", "light")
        state["accessibility_mode"] = bool((state["profile"] or {}).get("accessibility_mode", False))
        apply_theme()
        render_after_login()

    def load_profile() -> None:
        data = api_request("GET", "/me")
        state["user"] = data
        state["profile"] = data.get("profile")
        state["theme_mode"] = (state["profile"] or {}).get("theme_mode", "light")
        state["accessibility_mode"] = bool((state["profile"] or {}).get("accessibility_mode", False))
        apply_theme()

    def render_after_login() -> None:
        profile = state.get("profile") or {}
        if not profile.get("physical_questionnaire_completed"):
            render_physical_questionnaire()
        else:
            render_onboarding()

    def logout(_: Any = None) -> None:
        state.update({"token": None, "user": None, "profile": None, "selected_match": None})
        try:
            page.client_storage.remove("matchai_token")
        except Exception:
            pass
        render_login()

    def shell(title: str, active: str, body: ft.Control) -> None:
        apply_theme()
        palette = colors()
        nav_items = [
            ("Chat IA", ft.Icons.CHAT_BUBBLE_OUTLINE, render_onboarding, "chat"),
            ("Matches", ft.Icons.FAVORITE_BORDER, render_matches, "matches"),
            ("Perfil", ft.Icons.PERSON_OUTLINE, render_profile, "profile"),
            ("Ajustes", ft.Icons.TUNE, render_settings, "settings"),
        ]
        nav = ft.Row(
            controls=[
                app_button(
                    label,
                    icon=icon,
                    on_click=lambda e, handler=handler: handler(),
                    palette=palette,
                    kind="primary" if key == active else "surface",
                    tooltip=label,
                )
                for label, icon, handler, key in nav_items
            ],
            spacing=8,
            wrap=True,
        )
        page.clean()
        page.add(
            ft.Container(
                expand=True,
                padding=24,
                bgcolor=palette["bg"],
                content=ft.Column(
                    expand=True,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "MatchAI",
                                            size=sp(30),
                                            weight=ft.FontWeight.BOLD,
                                            color=palette["primary"],
                                        ),
                                        ft.Text(title, size=sp(15), color=palette["muted"]),
                                    ],
                                    spacing=0,
                                ),
                                ft.Container(expand=True),
                                nav,
                                app_icon_button(
                                    icon=ft.Icons.LOGOUT,
                                    tooltip="Sair",
                                    on_click=logout,
                                    palette=palette,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        body,
                    ],
                ),
            )
        )
        page.update()

    def panel(content: ft.Control, padding: int = 18, expand: bool = False) -> ft.Container:
        palette = colors()
        return ft.Container(
            content=content,
            padding=padding,
            expand=expand,
            bgcolor=palette["surface"],
            border=ft.border.all(2 if state.get("accessibility_mode") else 1, palette["border"]),
            border_radius=18,
        )

    def section_title(text: str) -> ft.Text:
        return ft.Text(text, size=sp(18), weight=ft.FontWeight.BOLD, color=colors()["text"])

    def render_login() -> None:
        apply_theme()
        palette = colors()
        email = ft.TextField(label="E-mail", border_color=palette["accent"])
        password = ft.TextField(
            label="Senha",
            password=True,
            can_reveal_password=True,
            border_color=palette["accent"],
        )
        display_name = ft.TextField(label="Nome para exibiÃ§Ã£o", border_color=palette["accent"])
        status = ft.Text("", color=palette["muted"])

        async def submit_login(event: Any) -> None:
            async def work() -> None:
                payload = await api_request_async(
                    "POST",
                    "/auth/login",
                    {"email": email.value, "password": password.value},
                    auth=False,
                )
                await save_session_async(payload)

            await run_guarded(event, work, status=status, busy_text="Entrando...")

        async def submit_register(event: Any) -> None:
            async def work() -> None:
                payload = await api_request_async(
                    "POST",
                    "/auth/register",
                    {
                        "email": email.value,
                        "password": password.value,
                        "display_name": display_name.value,
                    },
                    auth=False,
                )
                await save_session_async(payload)

            await run_guarded(event, work, status=status, busy_text="Criando conta...")

        async def poll_google(state_value: str) -> None:
            for _ in range(60):
                await asyncio.sleep(2)
                try:
                    data = await asyncio.to_thread(
                        api_request,
                        "GET",
                        f"/auth/google/status/{state_value}",
                        None,
                        False,
                    )
                    if data.get("status") == "done":
                        await save_session_async({"token": data["token"], "user": data["user"]})
                        return
                    if data.get("status") == "error":
                        status.value = data.get("error", "Erro no Google OAuth.")
                        page.update()
                        return
                except Exception as exc:
                    status.value = str(exc)
                    page.update()
                    return
            status.value = "Tempo de login Google expirou."
            page.update()

        async def google_login(event: Any) -> None:
            async def work() -> None:
                data = await api_request_async("GET", "/auth/google/start", auth=False)
                if not data.get("enabled"):
                    status.value = data.get("mensagem", "Google OAuth indisponÃ­vel.")
                    page.update()
                    return
                page.launch_url(data["auth_url"])
                status.value = "Finalize o login no navegador. Vou esperar aqui."
                page.update()
                page.run_task(poll_google, data["state"])

            await run_guarded(event, work, status=status, busy_text="Abrindo login do Google...")

        page.clean()
        page.add(
            ft.Container(
                expand=True,
                bgcolor=palette["bg"],
                padding=32,
                content=ft.Row(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=430,
                            padding=30,
                            bgcolor=palette["surface"],
                            border_radius=24,
                            border=ft.border.all(1, palette["border"]),
                            content=ft.Column(
                                spacing=16,
                                controls=[
                                    ft.Text(
                                        "MatchAI",
                                        size=42,
                                        weight=ft.FontWeight.BOLD,
                                        color=palette["primary"],
                                    ),
                                    ft.Text(
                                        "Crie conexÃµes por valores, rotina e afinidade real.",
                                        size=16,
                                        color=palette["muted"],
                                    ),
                                    ft.Text(
                                        "Entre para continuar seu perfil, suas conversas e seus matches.",
                                        size=13,
                                        color=palette["muted"],
                                    ),
                                    email,
                                    password,
                                    display_name,
                                    ft.Row(
                                        controls=[
                                            primary_button(
                                                "Entrar",
                                                icon=ft.Icons.LOGIN,
                                                on_click=submit_login,
                                                palette=palette,
                                            ),
                                            secondary_button(
                                                "Criar conta",
                                                icon=ft.Icons.PERSON_ADD,
                                                on_click=submit_register,
                                                palette=palette,
                                            ),
                                        ],
                                    ),
                                    ft.Divider(color=palette["border"]),
                                    secondary_button(
                                        "Continuar com Google",
                                        icon=ft.Icons.PUBLIC,
                                        on_click=google_login,
                                        palette=palette,
                                    ),
                                    status,
                                ],
                            ),
                        )
                    ],
                ),
            )
        )
        page.update()

    def render_physical_questionnaire() -> None:
        apply_theme()
        palette = colors()
        profile = state.get("profile") or {}
        current = (profile.get("vector_json") or {}).get("fisico", {})
        category_fields: dict[str, ft.Dropdown] = {}
        toggle_fields: dict[str, ft.Dropdown] = {}
        gender_field = ft.Dropdown(
            label="Seu gÃªnero",
            width=300,
            value=profile.get("gender_identity") or "nao_informar",
            options=[
                ft.dropdown.Option(key, label)
                for key, label in GENDER_LABELS.items()
            ],
        )
        interest_field = ft.Dropdown(
            label="Quero conhecer",
            width=300,
            value=profile.get("interested_in") or "nao_informar",
            options=[
                ft.dropdown.Option(key, label)
                for key, label in INTERESTED_IN_LABELS.items()
            ],
        )
        status = ft.Text("", color=palette["muted"], size=sp(14))

        def category_value(keys: list[str]) -> str:
            for key in keys:
                if float(current.get(key, 0.5)) >= 0.75:
                    return key
            return "neutral"

        def toggle_value(key: str) -> str:
            value = float(current.get(key, 0.5))
            if value >= 0.75:
                return "yes"
            if value <= 0.25:
                return "no"
            return "neutral"

        category_controls: list[ft.Control] = []
        for label, keys in PHYSICAL_CATEGORIES:
            dropdown = ft.Dropdown(
                label=label,
                value=category_value(keys),
                options=[
                    ft.dropdown.Option("neutral", "Prefiro nÃ£o responder"),
                    *[
                        ft.dropdown.Option(key, PHYSICAL_LABELS.get(key, key))
                        for key in keys
                    ],
                ],
            )
            category_fields[label] = dropdown
            category_controls.append(dropdown)

        toggle_controls: list[ft.Control] = []
        for key in PHYSICAL_TOGGLES:
            dropdown = ft.Dropdown(
                label=PHYSICAL_LABELS.get(key, key),
                value=toggle_value(key),
                options=[
                    ft.dropdown.Option("neutral", "Prefiro nÃ£o responder"),
                    ft.dropdown.Option("yes", "Sim"),
                    ft.dropdown.Option("no", "NÃ£o"),
                ],
            )
            toggle_fields[key] = dropdown
            toggle_controls.append(dropdown)

        async def save_physical(event: Any) -> None:
            fisico = {key: 0.5 for key in PHYSICAL_VECTOR_SCHEMA.keys()}
            for label, keys in PHYSICAL_CATEGORIES:
                selected = category_fields[label].value or "neutral"
                if selected != "neutral":
                    for key in keys:
                        fisico[key] = 1.0 if key == selected else 0.0
            for key, dropdown in toggle_fields.items():
                selected = dropdown.value or "neutral"
                if selected == "yes":
                    fisico[key] = 1.0
                elif selected == "no":
                    fisico[key] = 0.0

            async def work() -> None:
                profile = await api_request_async(
                    "PATCH",
                    "/profile/physical",
                    {
                        "fisico": fisico,
                        "gender_identity": gender_field.value or "nao_informar",
                        "interested_in": interest_field.value or "nao_informar",
                    },
                )
                state["profile"] = profile
                status.value = "Tudo salvo. Agora a IA pode te conhecer melhor."
                render_onboarding()

            await run_guarded(event, work, status=status, busy_text="Salvando suas caracterÃ­sticas...")

        page.clean()
        page.add(
            ft.Container(
                expand=True,
                bgcolor=palette["bg"],
                padding=32,
                content=ft.Row(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=680,
                            padding=30,
                            bgcolor=palette["surface"],
                            border_radius=24,
                            border=ft.border.all(2 if state.get("accessibility_mode") else 1, palette["border"]),
                            content=ft.Column(
                                spacing=18,
                                scroll=ft.ScrollMode.AUTO,
                                controls=[
                                    ft.Text(
                                        "Conte sobre vocÃª",
                                        size=sp(34),
                                        weight=ft.FontWeight.BOLD,
                                        color=palette["primary"],
                                    ),
                                    ft.Text(
                                        "Escolha as opÃ§Ãµes que descrevem vocÃª. Se preferir, pode pular qualquer resposta.",
                                        size=sp(16),
                                        color=palette["muted"],
                                    ),
                                    section_title("Quem Ã© vocÃª"),
                                    ft.Row(
                                        wrap=True,
                                        spacing=12,
                                        controls=[gender_field, interest_field],
                                    ),
                                    section_title("Suas caracterÃ­sticas"),
                                    *category_controls,
                                    *toggle_controls,
                                    primary_button(
                                        "Salvar e conversar com a IA",
                                        icon=ft.Icons.CHECK_CIRCLE,
                                        on_click=save_physical,
                                        palette=palette,
                                    ),
                                    status,
                                ],
                            ),
                        )
                    ],
                ),
            )
        )
        page.update()

    def render_onboarding() -> None:
        palette = colors()
        profile = state.get("profile") or {}
        font_scale = float(profile.get("chat_font_scale", 1.0))
        history = api_request("GET", "/historico").get("historico", [])
        messages_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        input_field = ft.TextField(
            hint_text="Conte sobre vocÃª, sua rotina, seus gostos ou seus valores...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=3,
        )
        status = ft.Text("", color=palette["muted"])

        def add_bubble(remetente: str, mensagem: str) -> None:
            is_user = remetente == "usuario"
            bubble_color = palette["primary"] if is_user else palette["surface_alt"]
            text_color = "#FFFFFF" if is_user else palette["text"]
            messages_view.controls.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
                    controls=[
                        ft.Container(
                            width=560,
                            padding=14,
                            border_radius=18,
                            bgcolor=bubble_color,
                            content=ft.Text(
                                mensagem,
                                size=round(16 * font_scale),
                                color=text_color,
                            ),
                        )
                    ],
                )
            )

        for msg in history:
            add_bubble(msg["remetente"], msg["mensagem"])

        async def send_message(event: Any) -> None:
            text = (input_field.value or "").strip()
            if not text:
                return
            async def work() -> None:
                input_field.value = ""
                add_bubble("usuario", text)
                data = await api_request_async(
                    "POST",
                    "/chat",
                    {"texto": text},
                    True,
                    45,
                )
                add_bubble("ia", data.get("resposta", "NÃ£o consegui responder agora."))
                status.value = ""

            await run_guarded(event, work, status=status, busy_text="A IA estÃ¡ pensando...")

        async def analyze_profile(event: Any) -> None:
            async def work() -> None:
                data = await api_request_async("POST", "/analisar_perfil", {"texto": ""})
                state["profile"] = data["profile"]
                status.value = "Perfil atualizado."

            await run_guarded(event, work, status=status, busy_text="Atualizando seu perfil...")

        async def find_match(event: Any) -> None:
            async def work() -> None:
                data = await api_request_async("POST", "/dar_match", {"texto": ""}, True, 60)
                if data.get("sucesso"):
                    status.value = f"Deu match com {data['match']['nome']} ({data['match']['afinidade']})."
                    snack(status.value)
                    render_matches()
                else:
                    status.value = data.get("mensagem", "Nenhum match encontrado.")

            await run_guarded(event, work, status=status, busy_text="Buscando pessoas compatÃ­veis...")

        suggestions = [
            ("Hobbies", "Quero falar sobre meus hobbies e o que eu faÃ§o no tempo livre."),
            ("MÃºsica", "MÃºsica e arte dizem muito sobre mim. Vamos por esse caminho."),
            ("Rotina", "Quero contar como Ã© minha rotina e o ritmo de vida que combina comigo."),
            ("Valores", "Prefiro falar sobre meus valores, limites e visÃ£o de mundo."),
            ("RelaÃ§Ã£o", "Quero explicar que tipo de relaÃ§Ã£o e conexÃ£o profunda eu procuro."),
            ("PreferÃªncias", "Quero contar tambÃ©m que tipos de caracterÃ­sticas me atraem."),
        ]

        chips = ft.Row(
            wrap=True,
            spacing=8,
            controls=[
                secondary_button(
                    label,
                    on_click=lambda e, prompt=prompt: setattr(input_field, "value", prompt) or page.update(),
                    palette=palette,
                )
                for label, prompt in suggestions
            ],
        )

        body = ft.Column(
            expand=True,
            controls=[
                panel(
                    ft.Column(
                        controls=[
                            section_title("Converse com a IA"),
                            chips,
                            status,
                        ]
                    )
                ),
                panel(messages_view, expand=True),
                ft.Container(
                    padding=12,
                    bgcolor=palette["surface"],
                    border_radius=18,
                    border=ft.border.all(1, palette["border"]),
                    content=ft.Row(
                        controls=[
                            input_field,
                            app_icon_button(
                                icon=ft.Icons.SEND,
                                tooltip="Enviar",
                                on_click=send_message,
                                palette=palette,
                            ),
                            secondary_button(
                                "Atualizar perfil",
                                icon=ft.Icons.AUTO_AWESOME,
                                on_click=analyze_profile,
                                palette=palette,
                            ),
                            primary_button(
                                "Dar match",
                                icon=ft.Icons.FAVORITE,
                                on_click=find_match,
                                palette=palette,
                            ),
                        ]
                    ),
                ),
            ],
        )
        shell("Conte sobre vocÃª", "chat", body)

    def render_matches() -> None:
        palette = colors()
        data = api_request("GET", "/matches")
        matches = data.get("matches", [])
        controls: list[ft.Control] = [section_title("Seus matches")]
        if not matches:
            controls.append(
                ft.Text(
                    "Converse com a IA e use Dar match para encontrar pessoas compatÃ­veis.",
                    color=palette["muted"],
                )
            )
        for match in matches:
            controls.append(
                panel(
                    ft.Row(
                        controls=[
                            ft.Column(
                                expand=True,
                                controls=[
                                    ft.Text(
                                        match["matched_name"],
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                        color=palette["text"],
                                    ),
                                    ft.Text(
                                        f"{round(float(match['affinity']), 1)}% de afinidade",
                                        color=palette["primary"],
                                    ),
                                    ft.Text(match.get("explanation", ""), color=palette["muted"]),
                                ],
                            ),
                            primary_button(
                                "Expandir",
                                icon=ft.Icons.OPEN_IN_FULL,
                                on_click=lambda e, match_id=match["id"]: render_match_detail(match_id),
                                palette=palette,
                            ),
                        ]
                    )
                )
            )
        body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=controls)
        shell("Pessoas com interesses e valores compatÃ­veis", "matches", body)

    def render_match_detail(match_id: str) -> None:
        palette = colors()
        detail = api_request("GET", f"/matches/{match_id}/profile")
        messages = api_request("GET", f"/matches/{match_id}/messages").get("messages", [])
        match = detail["match"]
        profile = detail["profile"]
        public_profile = profile.get("public_profile", {})
        top_interests = profile.get("top_interests_summary", [])
        breakdown = profile.get("compatibility_breakdown", {})
        message_field = ft.TextField(hint_text="Escreva uma mensagem para este match...", expand=True)
        icebreaker_text = ft.Text("", color=palette["primary"])
        messages_view = ft.ListView(height=220, spacing=8, auto_scroll=True)

        def add_match_message(item: dict[str, Any]) -> None:
            mine = item.get("sender_user_id") == (state.get("user") or {}).get("id")
            messages_view.controls.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.END if mine else ft.MainAxisAlignment.START,
                    controls=[
                        ft.Container(
                            padding=10,
                            border_radius=14,
                            bgcolor=palette["primary"] if mine else palette["surface_alt"],
                            content=ft.Text(
                                item["mensagem"],
                                color="#FFFFFF" if mine else palette["text"],
                            ),
                        )
                    ],
                )
            )

        for item in messages:
            add_match_message(item)

        def render_group(group_name: str, values: dict[str, Any]) -> ft.Control:
            if group_name == "interesses":
                labels = INTEREST_LABELS
            elif group_name == "fisico":
                labels = PHYSICAL_LABELS
            else:
                labels = VALUE_LABELS
            rows = [
                ft.Text(
                    f"{labels.get(key, key)}: {round(float(value) * 100)}%",
                    color=palette["muted"],
                )
                for key, value in values.items()
            ]
            return ft.Column(controls=[section_title(GROUP_LABELS.get(group_name, group_name.title())), *rows])

        async def load_icebreaker(event: Any) -> None:
            async def work() -> None:
                data = await api_request_async("POST", f"/matches/{match_id}/icebreaker")
                icebreaker_text.value = data.get("sugestao", "")

            await run_guarded(event, work, status=icebreaker_text, busy_text="Gerando sugestÃ£o...")

        async def send_match_message(event: Any) -> None:
            text = (message_field.value or "").strip()
            if not text:
                return
            async def work() -> None:
                message_field.value = ""
                data = await api_request_async(
                    "POST",
                    f"/matches/{match_id}/messages",
                    {"mensagem": text},
                )
                add_match_message(data["message"])

            await run_guarded(event, work)

        photo_path = profile.get("photo_path", "")
        photo_control: ft.Control
        if photo_path:
            photo_control = ft.Container(
                width=150,
                height=150,
                border_radius=18,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Image(src=photo_path, width=150, height=150, fit=ft.ImageFit.COVER),
            )
        else:
            photo_control = ft.Container(
                width=150,
                height=150,
                border_radius=18,
                bgcolor=palette["surface_alt"],
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.PERSON, size=64, color=palette["primary"]),
            )

        interest_chips = ft.Row(
            wrap=True,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    border_radius=20,
                    bgcolor=palette["surface_alt"],
                    content=ft.Text(item.get("label", ""), color=palette["primary"], size=sp(13)),
                )
                for item in top_interests
            ],
        )

        profile_controls: list[ft.Control] = [
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    photo_control,
                    ft.Column(
                        expand=True,
                        controls=[
                            ft.Text(profile["nome"], size=sp(28), weight=ft.FontWeight.BOLD, color=palette["text"]),
                            ft.Text(profile.get("bio", ""), color=palette["muted"], size=sp(14)),
                            ft.Text(match.get("explanation", ""), color=palette["primary"], size=sp(14)),
                            interest_chips,
                        ],
                    ),
                ],
            ),
            ft.Row(
                wrap=True,
                spacing=10,
                controls=[
                    ft.Container(
                        padding=12,
                        border_radius=14,
                        bgcolor=palette["surface_alt"],
                        content=ft.Text(
                            f"Interesses e valores {breakdown.get('base_similarity', 0)}%",
                            color=palette["text"],
                        ),
                    ),
                    ft.Container(
                        padding=12,
                        border_radius=14,
                        bgcolor=palette["surface_alt"],
                        content=ft.Text(
                            f"Sintonia visual {breakdown.get('physical_similarity', 0)}%",
                            color=palette["text"],
                        ),
                    ),
                    ft.Container(
                        padding=12,
                        border_radius=14,
                        bgcolor=palette["surface_alt"],
                        content=ft.Text(
                            f"Afinidade {breakdown.get('overall_affinity', match.get('affinity', 0))}%",
                            color=palette["primary"],
                            weight=ft.FontWeight.BOLD,
                        ),
                    ),
                ],
            ),
        ]
        for group, values in public_profile.items():
            if isinstance(values, dict):
                profile_controls.append(render_group(group, values))

        body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row(
                    controls=[
                        secondary_button(
                            "Voltar",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: render_matches(),
                            palette=palette,
                        )
                    ]
                ),
                panel(ft.Column(controls=profile_controls, spacing=12)),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Primeiro assunto"),
                            icebreaker_text,
                            secondary_button(
                                "Sugerir assunto",
                                icon=ft.Icons.LIGHTBULB,
                                on_click=load_icebreaker,
                                palette=palette,
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Conversa salva"),
                            messages_view,
                            ft.Row(
                                controls=[
                                    message_field,
                                    app_icon_button(
                                        icon=ft.Icons.SEND,
                                        tooltip="Enviar mensagem",
                                        on_click=send_match_message,
                                        palette=palette,
                                    ),
                                ]
                            ),
                        ]
                    )
                ),
            ],
        )
        shell("Perfil e conversa", "matches", body)

    def render_profile() -> None:
        palette = colors()
        profile = api_request("GET", "/profile")
        saved_filters = {
            item["key"]: item
            for item in api_request("GET", "/profile/value-filters").get("filters", [])
        }
        state["profile"] = profile
        vectors = profile.get("vector_json") or profile.get("profile_json") or default_profile_vectors()
        physical_current = vectors.get("fisico", {})
        display_name = ft.TextField(label="Nome pÃºblico", value=profile.get("display_name", ""))
        bio = ft.TextField(label="Bio pÃºblica", value=profile.get("bio", ""), multiline=True, min_lines=2)
        gender_field = ft.Dropdown(
            label="Seu gÃªnero",
            width=300,
            value=profile.get("gender_identity") or "nao_informar",
            options=[ft.dropdown.Option(key, label) for key, label in GENDER_LABELS.items()],
        )
        interest_field = ft.Dropdown(
            label="Quero conhecer",
            width=300,
            value=profile.get("interested_in") or "nao_informar",
            options=[ft.dropdown.Option(key, label) for key, label in INTERESTED_IN_LABELS.items()],
        )
        visibility = profile.get("visible_fields", {})
        visibility_checks = {
            "bio": ft.Checkbox(label="Mostrar bio", value=visibility.get("bio", True)),
            "interesses": ft.Checkbox(label="Mostrar interesses", value=visibility.get("interesses", True)),
            "valores": ft.Checkbox(label="Mostrar valores", value=visibility.get("valores", False)),
            "psicologico": ft.Checkbox(label="Mostrar traÃ§os pessoais", value=visibility.get("psicologico", False)),
            "fisico": ft.Checkbox(label="Mostrar caracterÃ­sticas fÃ­sicas", value=visibility.get("fisico", False)),
        }
        interest_sliders = {
            key: ft.Slider(
                min=0,
                max=1,
                divisions=10,
                value=float(vectors.get("interesses", {}).get(key, 0.5)),
                label="{value}",
            )
            for key in INTEREST_KEYS
        }
        def category_value(keys: list[str]) -> str:
            for key in keys:
                if float(physical_current.get(key, 0.5)) >= 0.75:
                    return key
            return "neutral"

        def toggle_value(key: str) -> str:
            value = float(physical_current.get(key, 0.5))
            if value >= 0.75:
                return "yes"
            if value <= 0.25:
                return "no"
            return "neutral"

        category_fields: dict[str, ft.Dropdown] = {}
        toggle_fields: dict[str, ft.Dropdown] = {}
        for label, keys in PHYSICAL_CATEGORIES:
            category_fields[label] = ft.Dropdown(
                label=label,
                value=category_value(keys),
                options=[
                    ft.dropdown.Option("neutral", "Prefiro nÃ£o responder"),
                    *[ft.dropdown.Option(key, PHYSICAL_LABELS.get(key, key)) for key in keys],
                ],
            )
        for key in PHYSICAL_TOGGLES:
            toggle_fields[key] = ft.Dropdown(
                label=PHYSICAL_LABELS.get(key, key),
                value=toggle_value(key),
                options=[
                    ft.dropdown.Option("neutral", "Prefiro nÃ£o responder"),
                    ft.dropdown.Option("yes", "Sim"),
                    ft.dropdown.Option("no", "NÃ£o"),
                ],
            )
        filter_delta = {
            key: ft.Slider(
                min=0.05,
                max=1,
                divisions=19,
                value=float(saved_filters.get(key, {}).get("max_delta") or 0.35),
                label="{value}",
            )
            for key in FILTER_KEYS
        }
        filter_active = {
            key: ft.Checkbox(
                label=VALUE_LABELS.get(key.split(".", 1)[-1], key),
                value=bool(saved_filters.get(key, {}).get("active", False)),
            )
            for key in FILTER_KEYS
        }
        status = ft.Text("", color=palette["muted"])
        selected_photo_path = {"value": profile.get("photo_path", "")}

        def photo_preview(path: str) -> ft.Control:
            if path:
                return ft.Container(
                    width=140,
                    height=140,
                    border_radius=18,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Image(src=path, width=140, height=140, fit=ft.ImageFit.COVER),
                )
            return ft.Container(
                width=140,
                height=140,
                border_radius=18,
                bgcolor=palette["surface_alt"],
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.ADD_A_PHOTO, size=48, color=palette["primary"]),
            )

        photo_box = ft.Container(content=photo_preview(selected_photo_path["value"]))

        async def choose_photo(event: Any) -> None:
            async def work() -> None:
                files = await photo_picker.pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                )
                if not files:
                    status.value = "Nenhuma foto selecionada."
                    return
                selected_photo_path["value"] = files[0].path or ""
                if not selected_photo_path["value"]:
                    status.value = "NÃ£o consegui acessar o caminho da foto."
                    return
                updated = await api_request_async(
                    "PATCH",
                    "/profile/photo",
                    {"photo_path": selected_photo_path["value"]},
                )
                state["profile"] = updated
                photo_box.content = photo_preview(selected_photo_path["value"])
                status.value = "Foto salva no perfil."

            await run_guarded(event, work, status=status, busy_text="Escolhendo foto...")

        async def save_basic(event: Any) -> None:
            async def work() -> None:
                updated = await api_request_async(
                    "PATCH",
                    "/profile",
                    {
                        "display_name": display_name.value,
                        "bio": bio.value,
                        "gender_identity": gender_field.value or "nao_informar",
                        "interested_in": interest_field.value or "nao_informar",
                    },
                )
                state["profile"] = updated
                status.value = "Perfil salvo."

            await run_guarded(event, work, status=status, busy_text="Salvando perfil...")

        async def save_interests(event: Any) -> None:
            async def work() -> None:
                updated = await api_request_async(
                    "PATCH",
                    "/profile/interests",
                    {"interests": {key: slider.value for key, slider in interest_sliders.items()}},
                )
                state["profile"] = updated
                status.value = "Interesses atualizados."

            await run_guarded(event, work, status=status, busy_text="Salvando interesses...")

        async def save_physical(event: Any) -> None:
            fisico = {key: 0.5 for key in PHYSICAL_VECTOR_SCHEMA.keys()}
            for label, keys in PHYSICAL_CATEGORIES:
                selected = category_fields[label].value or "neutral"
                if selected != "neutral":
                    for key in keys:
                        fisico[key] = 1.0 if key == selected else 0.0
            for key, dropdown in toggle_fields.items():
                selected = dropdown.value or "neutral"
                if selected == "yes":
                    fisico[key] = 1.0
                elif selected == "no":
                    fisico[key] = 0.0
            async def work() -> None:
                updated = await api_request_async(
                    "PATCH",
                    "/profile/physical",
                    {
                        "fisico": fisico,
                        "gender_identity": gender_field.value or "nao_informar",
                        "interested_in": interest_field.value or "nao_informar",
                    },
                )
                state["profile"] = updated
                status.value = "CaracterÃ­sticas atualizadas."

            await run_guarded(event, work, status=status, busy_text="Salvando caracterÃ­sticas...")

        async def save_visibility(event: Any) -> None:
            async def work() -> None:
                updated = await api_request_async(
                    "PATCH",
                    "/profile/visibility",
                    {"visible_fields": {key: box.value for key, box in visibility_checks.items()}},
                )
                state["profile"] = updated
                status.value = "Privacidade atualizada."

            await run_guarded(event, work, status=status, busy_text="Salvando privacidade...")

        async def save_filters(event: Any) -> None:
            async def work() -> None:
                await api_request_async(
                    "PATCH",
                    "/profile/value-filters",
                    {
                        "filters": [
                            {
                                "key": key,
                                "active": filter_active[key].value,
                                "max_delta": filter_delta[key].value,
                            }
                            for key in FILTER_KEYS
                        ]
                    },
                )
                status.value = "Filtros de valores salvos."

            await run_guarded(event, work, status=status, busy_text="Salvando filtros...")

        interests_controls: list[ft.Control] = []
        for key, slider in interest_sliders.items():
            interests_controls.append(ft.Text(INTEREST_LABELS.get(key, key), color=palette["text"]))
            interests_controls.append(slider)

        physical_controls: list[ft.Control] = []
        for dropdown in category_fields.values():
            physical_controls.append(dropdown)
        for dropdown in toggle_fields.values():
            physical_controls.append(dropdown)

        filter_controls: list[ft.Control] = []
        for key in FILTER_KEYS:
            filter_controls.append(filter_active[key])
            filter_controls.append(ft.Text("Quanto pode variar", color=palette["muted"]))
            filter_controls.append(filter_delta[key])

        body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                panel(
                    ft.Column(
                        controls=[
                            section_title("Foto"),
                            ft.Row(
                                controls=[
                                    photo_box,
                                    ft.Column(
                                        expand=True,
                                        controls=[
                                            ft.Text("Foto de perfil", color=palette["muted"]),
                                            secondary_button(
                                                "Escolher foto",
                                                icon=ft.Icons.ADD_A_PHOTO,
                                                on_click=choose_photo,
                                                palette=palette,
                                            ),
                                        ],
                                    ),
                                ]
                            ),
                            section_title("Sobre vocÃª"),
                            display_name,
                            bio,
                            section_title("Quem vocÃª quer conhecer"),
                            ft.Row(
                                wrap=True,
                                spacing=12,
                                controls=[gender_field, interest_field],
                            ),
                            primary_button(
                                "Salvar perfil",
                                icon=ft.Icons.SAVE,
                                on_click=save_basic,
                                palette=palette,
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Suas caracterÃ­sticas"),
                            ft.Text(
                                "Atualize as informaÃ§Ãµes que ajudam outras pessoas a conhecerem vocÃª.",
                                color=palette["muted"],
                            ),
                            *physical_controls,
                            primary_button(
                                "Salvar caracterÃ­sticas",
                                icon=ft.Icons.ACCESSIBILITY_NEW,
                                on_click=save_physical,
                                palette=palette,
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Interesses"),
                            *interests_controls,
                            primary_button(
                                "Salvar interesses",
                                icon=ft.Icons.TUNE,
                                on_click=save_interests,
                                palette=palette,
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Privacidade"),
                            *visibility_checks.values(),
                            primary_button(
                                "Salvar privacidade",
                                icon=ft.Icons.VISIBILITY,
                                on_click=save_visibility,
                                palette=palette,
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Filtros de valores"),
                            *filter_controls,
                            primary_button(
                                "Salvar filtros",
                                icon=ft.Icons.FILTER_ALT,
                                on_click=save_filters,
                                palette=palette,
                            ),
                            status,
                        ]
                    )
                ),
            ],
        )
        shell("Seu perfil e privacidade", "profile", body)

    def render_settings() -> None:
        palette = colors()
        profile = api_request("GET", "/profile")
        theme_switch = ft.Switch(label="Modo escuro", value=profile.get("theme_mode") == "dark")
        accessibility_switch = ft.Switch(
            label="Modo acessibilidade visual",
            value=bool(profile.get("accessibility_mode", False)),
        )
        font_slider = ft.Slider(
            min=0.8,
            max=1.6,
            divisions=8,
            value=float(profile.get("chat_font_scale", 1.0)),
            label="{value}",
        )
        ui_font_slider = ft.Slider(
            min=0.8,
            max=1.8,
            divisions=10,
            value=float(profile.get("ui_font_scale", 1.0)),
            label="{value}",
        )
        export_text = ft.Text("", selectable=True, color=palette["muted"])
        status = ft.Text("", color=palette["muted"])

        async def save_settings(event: Any) -> None:
            async def work() -> None:
                updated = await api_request_async(
                    "PATCH",
                    "/profile",
                    {
                        "theme_mode": "dark" if theme_switch.value else "light",
                        "chat_font_scale": font_slider.value,
                        "ui_font_scale": ui_font_slider.value,
                        "accessibility_mode": accessibility_switch.value,
                    },
                )
                state["profile"] = updated
                state["theme_mode"] = updated.get("theme_mode", "light")
                state["accessibility_mode"] = bool(updated.get("accessibility_mode", False))
                status.value = "Ajustes salvos."
                render_settings()

            await run_guarded(event, work, status=status, busy_text="Salvando ajustes...")

        async def export_data(event: Any) -> None:
            async def work() -> None:
                data = await api_request_async("GET", "/profile/export")
                export_text.value = str(data)

            await run_guarded(event, work, status=export_text, busy_text="Preparando seus dados...")

        async def delete_data(event: Any) -> None:
            async def work() -> None:
                data = await api_request_async("DELETE", "/profile")
                status.value = data.get("mensagem", "Dados apagados.")
                refreshed = await api_request_async("GET", "/me")
                state["user"] = refreshed
                state["profile"] = refreshed.get("profile")
                state["theme_mode"] = (state["profile"] or {}).get("theme_mode", "light")
                state["accessibility_mode"] = bool((state["profile"] or {}).get("accessibility_mode", False))
                render_settings()

            await run_guarded(event, work, status=status, busy_text="Apagando perfil...")

        body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                panel(
                    ft.Column(
                        controls=[
                            section_title("Conforto visual"),
                            theme_switch,
                            accessibility_switch,
                            ft.Text("Tamanho da fonte do chat", color=palette["muted"]),
                            font_slider,
                            ft.Text("Tamanho geral da interface", color=palette["muted"]),
                            ui_font_slider,
                            primary_button(
                                "Salvar ajustes",
                                icon=ft.Icons.SAVE,
                                on_click=save_settings,
                                palette=palette,
                            ),
                            status,
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Autonomia sobre dados"),
                            ft.Row(
                                controls=[
                                    secondary_button(
                                        "Exportar dados",
                                        icon=ft.Icons.DOWNLOAD,
                                        on_click=export_data,
                                        palette=palette,
                                    ),
                                    danger_button(
                                        "Apagar perfil",
                                        icon=ft.Icons.DELETE,
                                        on_click=delete_data,
                                        palette=palette,
                                    ),
                                ]
                            ),
                            export_text,
                        ]
                    )
                ),
            ],
        )
        shell("Modo escuro, fonte do chat e dados", "settings", body)

    try:
        saved_token = page.client_storage.get("matchai_token")
    except Exception:
        saved_token = None

    if saved_token:
        state["token"] = saved_token
        try:
            load_profile()
            render_after_login()
        except Exception:
            render_login()
    else:
        render_login()


if __name__ == "__main__":
    ft.run(main)


from __future__ import annotations

import asyncio
import os
from typing import Any

import flet as ft
import requests

from src.schema.schema_vetores import INTEREST_LABELS, VALUE_LABELS, default_profile_vectors


API_BASE = os.getenv("MATCHAI_API_URL", "http://127.0.0.1:8000")

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


def main(page: ft.Page):
    state: dict[str, Any] = {
        "token": None,
        "user": None,
        "profile": None,
        "theme_mode": "light",
        "selected_match": None,
    }

    page.title = "MatchAI"
    page.window_width = 1100
    page.window_height = 760
    page.padding = 0

    def colors() -> dict[str, str]:
        return DARK if state.get("theme_mode") == "dark" else LIGHT

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
        response = requests.request(
            method,
            f"{API_BASE}{path}",
            json=json_body,
            headers=headers,
            timeout=timeout,
        )
        try:
            data = response.json()
        except ValueError:
            data = {"detail": response.text}
        if response.status_code >= 400:
            raise RuntimeError(data.get("detail") or data)
        return data

    def save_session(payload: dict[str, Any]) -> None:
        state["token"] = payload["token"]
        state["user"] = payload.get("user")
        try:
            page.client_storage.set("matchai_token", state["token"])
        except Exception:
            pass
        load_profile()
        render_onboarding()

    def load_profile() -> None:
        data = api_request("GET", "/me")
        state["user"] = data
        state["profile"] = data.get("profile")
        state["theme_mode"] = (state["profile"] or {}).get("theme_mode", "light")
        apply_theme()

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
                ft.ElevatedButton(
                    text=label,
                    icon=icon,
                    on_click=lambda e, handler=handler: handler(),
                    style=ft.ButtonStyle(
                        bgcolor=palette["primary"] if key == active else palette["surface"],
                        color="#FFFFFF" if key == active else palette["primary"],
                    ),
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
                                            size=30,
                                            weight=ft.FontWeight.BOLD,
                                            color=palette["primary"],
                                        ),
                                        ft.Text(title, size=15, color=palette["muted"]),
                                    ],
                                    spacing=0,
                                ),
                                ft.Container(expand=True),
                                nav,
                                ft.IconButton(
                                    icon=ft.Icons.LOGOUT,
                                    tooltip="Sair",
                                    icon_color=palette["primary"],
                                    on_click=logout,
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
            border=ft.border.all(1, palette["border"]),
            border_radius=18,
        )

    def section_title(text: str) -> ft.Text:
        return ft.Text(text, size=18, weight=ft.FontWeight.BOLD, color=colors()["text"])

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
        display_name = ft.TextField(label="Nome para exibicao", border_color=palette["accent"])
        status = ft.Text("", color=palette["muted"])

        def submit_login(_: Any) -> None:
            try:
                payload = api_request(
                    "POST",
                    "/auth/login",
                    {"email": email.value, "password": password.value},
                    auth=False,
                )
                save_session(payload)
            except Exception as exc:
                status.value = str(exc)
                page.update()

        def submit_register(_: Any) -> None:
            try:
                payload = api_request(
                    "POST",
                    "/auth/register",
                    {
                        "email": email.value,
                        "password": password.value,
                        "display_name": display_name.value,
                    },
                    auth=False,
                )
                save_session(payload)
            except Exception as exc:
                status.value = str(exc)
                page.update()

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
                        save_session({"token": data["token"], "user": data["user"]})
                        return
                    if data.get("status") == "error":
                        status.value = data.get("error", "Erro no Google OAuth.")
                        page.update()
                        return
                except Exception as exc:
                    status.value = str(exc)
                    page.update()
                    return
            status.value = "Tempo de login Google expirado."
            page.update()

        def google_login(_: Any) -> None:
            try:
                data = api_request("GET", "/auth/google/start", auth=False)
                if not data.get("enabled"):
                    status.value = data.get("mensagem", "Google OAuth indisponivel.")
                    page.update()
                    return
                page.launch_url(data["auth_url"])
                status.value = "Finalize o login no navegador. Vou esperar aqui."
                page.update()
                page.run_task(poll_google, data["state"])
            except Exception as exc:
                status.value = str(exc)
                page.update()

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
                                        "Crie conexoes por valores, rotina e afinidade real.",
                                        size=16,
                                        color=palette["muted"],
                                    ),
                                    email,
                                    password,
                                    display_name,
                                    ft.Row(
                                        controls=[
                                            ft.ElevatedButton(
                                                "Entrar",
                                                icon=ft.Icons.LOGIN,
                                                on_click=submit_login,
                                                style=ft.ButtonStyle(
                                                    bgcolor=palette["primary"],
                                                    color="#FFFFFF",
                                                ),
                                            ),
                                            ft.OutlinedButton(
                                                "Criar conta",
                                                icon=ft.Icons.PERSON_ADD,
                                                on_click=submit_register,
                                            ),
                                        ],
                                    ),
                                    ft.Divider(color=palette["border"]),
                                    ft.OutlinedButton(
                                        "Continuar com Google",
                                        icon=ft.Icons.PUBLIC,
                                        on_click=google_login,
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
            hint_text="Conte sobre voce, sua rotina, seus gostos ou seus valores...",
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

        async def send_message() -> None:
            text = (input_field.value or "").strip()
            if not text:
                return
            input_field.value = ""
            add_bubble("usuario", text)
            status.value = "A IA esta pensando..."
            page.update()
            try:
                data = await asyncio.to_thread(
                    api_request,
                    "POST",
                    "/chat",
                    {"texto": text},
                    True,
                    45,
                )
                add_bubble("ia", data.get("resposta", "Nao consegui responder agora."))
                status.value = ""
            except Exception as exc:
                status.value = str(exc)
            page.update()

        def send_clicked(_: Any) -> None:
            page.run_task(send_message)

        async def analyze_profile() -> None:
            status.value = "Atualizando seu perfil dinamico..."
            page.update()
            try:
                data = await asyncio.to_thread(api_request, "POST", "/analisar_perfil", {"texto": ""})
                state["profile"] = data["profile"]
                status.value = "Perfil atualizado com base no historico."
            except Exception as exc:
                status.value = str(exc)
            page.update()

        async def find_match() -> None:
            status.value = "Buscando compatibilidades por proximidade vetorial..."
            page.update()
            try:
                data = await asyncio.to_thread(api_request, "POST", "/dar_match", {"texto": ""}, True, 60)
                if data.get("sucesso"):
                    status.value = f"Deu match com {data['match']['nome']} ({data['match']['afinidade']})."
                    snack(status.value)
                    render_matches()
                else:
                    status.value = data.get("mensagem", "Nenhum match encontrado.")
            except Exception as exc:
                status.value = str(exc)
            page.update()

        suggestions = [
            ("Hobbies", "Quero falar sobre meus hobbies e o que eu faco no tempo livre."),
            ("Musica", "Musica e arte dizem muito sobre mim. Vamos por esse caminho."),
            ("Rotina", "Quero contar como e minha rotina e o ritmo de vida que combina comigo."),
            ("Valores", "Prefiro falar sobre meus valores, limites e visao de mundo."),
            ("Relacao", "Quero explicar que tipo de relacao e conexao profunda eu procuro."),
        ]

        chips = ft.Row(
            wrap=True,
            spacing=8,
            controls=[
                ft.OutlinedButton(
                    label,
                    on_click=lambda e, prompt=prompt: setattr(input_field, "value", prompt) or page.update(),
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
                            ft.IconButton(
                                icon=ft.Icons.SEND,
                                icon_color=palette["primary"],
                                tooltip="Enviar",
                                on_click=send_clicked,
                            ),
                            ft.ElevatedButton(
                                "Atualizar perfil",
                                icon=ft.Icons.AUTO_AWESOME,
                                on_click=lambda e: page.run_task(analyze_profile),
                                style=ft.ButtonStyle(bgcolor=palette["surface_alt"], color=palette["primary"]),
                            ),
                            ft.ElevatedButton(
                                "Dar match",
                                icon=ft.Icons.FAVORITE,
                                on_click=lambda e: page.run_task(find_match),
                                style=ft.ButtonStyle(bgcolor=palette["primary"], color="#FFFFFF"),
                            ),
                        ]
                    ),
                ),
            ],
        )
        shell("Onboarding inteligente e perfil dinamico", "chat", body)

    def render_matches() -> None:
        palette = colors()
        data = api_request("GET", "/matches")
        matches = data.get("matches", [])
        controls: list[ft.Control] = [section_title("Seus matches")]
        if not matches:
            controls.append(
                ft.Text(
                    "Converse com a IA e use Dar match para encontrar pessoas compativeis.",
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
                            ft.ElevatedButton(
                                "Expandir",
                                icon=ft.Icons.OPEN_IN_FULL,
                                on_click=lambda e, match_id=match["id"]: render_match_detail(match_id),
                                style=ft.ButtonStyle(bgcolor=palette["primary"], color="#FFFFFF"),
                            ),
                        ]
                    )
                )
            )
        body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=controls)
        shell("Pessoas com interesses e valores compativeis", "matches", body)

    def render_match_detail(match_id: str) -> None:
        palette = colors()
        detail = api_request("GET", f"/matches/{match_id}/profile")
        messages = api_request("GET", f"/matches/{match_id}/messages").get("messages", [])
        match = detail["match"]
        profile = detail["profile"]
        public_profile = profile.get("public_profile", {})
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
            labels = INTEREST_LABELS if group_name == "interesses" else VALUE_LABELS
            rows = [
                ft.Text(
                    f"{labels.get(key, key)}: {round(float(value) * 100)}%",
                    color=palette["muted"],
                )
                for key, value in values.items()
            ]
            return ft.Column(controls=[section_title(group_name.title()), *rows])

        async def load_icebreaker() -> None:
            icebreaker_text.value = "Gerando sugestao..."
            page.update()
            try:
                data = await asyncio.to_thread(api_request, "POST", f"/matches/{match_id}/icebreaker")
                icebreaker_text.value = data.get("sugestao", "")
            except Exception as exc:
                icebreaker_text.value = str(exc)
            page.update()

        async def send_match_message() -> None:
            text = (message_field.value or "").strip()
            if not text:
                return
            message_field.value = ""
            try:
                data = await asyncio.to_thread(
                    api_request,
                    "POST",
                    f"/matches/{match_id}/messages",
                    {"mensagem": text},
                )
                add_match_message(data["message"])
            except Exception as exc:
                snack(str(exc))
            page.update()

        profile_controls: list[ft.Control] = [
            ft.Text(profile["nome"], size=28, weight=ft.FontWeight.BOLD, color=palette["text"]),
            ft.Text(profile.get("bio", ""), color=palette["muted"]),
            ft.Text(match.get("explanation", ""), color=palette["primary"]),
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
                        ft.TextButton("Voltar", icon=ft.Icons.ARROW_BACK, on_click=lambda e: render_matches())
                    ]
                ),
                panel(ft.Column(controls=profile_controls, spacing=12)),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Primeiro assunto"),
                            icebreaker_text,
                            ft.ElevatedButton(
                                "Sugerir assunto",
                                icon=ft.Icons.LIGHTBULB,
                                on_click=lambda e: page.run_task(load_icebreaker),
                                style=ft.ButtonStyle(bgcolor=palette["surface_alt"], color=palette["primary"]),
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
                                    ft.IconButton(
                                        icon=ft.Icons.SEND,
                                        icon_color=palette["primary"],
                                        on_click=lambda e: page.run_task(send_match_message),
                                    ),
                                ]
                            ),
                        ]
                    )
                ),
            ],
        )
        shell("Perfil expandido e conversa do match", "matches", body)

    def render_profile() -> None:
        palette = colors()
        profile = api_request("GET", "/profile")
        saved_filters = {
            item["key"]: item
            for item in api_request("GET", "/profile/value-filters").get("filters", [])
        }
        state["profile"] = profile
        vectors = profile.get("vector_json") or profile.get("profile_json") or default_profile_vectors()
        display_name = ft.TextField(label="Nome publico", value=profile.get("display_name", ""))
        bio = ft.TextField(label="Bio publica", value=profile.get("bio", ""), multiline=True, min_lines=2)
        visibility = profile.get("visible_fields", {})
        visibility_checks = {
            "bio": ft.Checkbox(label="Mostrar bio", value=visibility.get("bio", True)),
            "interesses": ft.Checkbox(label="Mostrar interesses", value=visibility.get("interesses", True)),
            "valores": ft.Checkbox(label="Mostrar valores", value=visibility.get("valores", False)),
            "psicologico": ft.Checkbox(label="Mostrar perfil psicologico", value=visibility.get("psicologico", False)),
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
                label=key.replace("valores.", ""),
                value=bool(saved_filters.get(key, {}).get("active", False)),
            )
            for key in FILTER_KEYS
        }
        status = ft.Text("", color=palette["muted"])

        def save_basic(_: Any) -> None:
            try:
                updated = api_request(
                    "PATCH",
                    "/profile",
                    {
                        "display_name": display_name.value,
                        "bio": bio.value,
                    },
                )
                state["profile"] = updated
                status.value = "Perfil salvo."
            except Exception as exc:
                status.value = str(exc)
            page.update()

        def save_interests(_: Any) -> None:
            try:
                updated = api_request(
                    "PATCH",
                    "/profile/interests",
                    {"interests": {key: slider.value for key, slider in interest_sliders.items()}},
                )
                state["profile"] = updated
                status.value = "Interesses atualizados."
            except Exception as exc:
                status.value = str(exc)
            page.update()

        def save_visibility(_: Any) -> None:
            try:
                updated = api_request(
                    "PATCH",
                    "/profile/visibility",
                    {"visible_fields": {key: box.value for key, box in visibility_checks.items()}},
                )
                state["profile"] = updated
                status.value = "Privacidade atualizada."
            except Exception as exc:
                status.value = str(exc)
            page.update()

        def save_filters(_: Any) -> None:
            try:
                api_request(
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
            except Exception as exc:
                status.value = str(exc)
            page.update()

        interests_controls: list[ft.Control] = []
        for key, slider in interest_sliders.items():
            interests_controls.append(ft.Text(INTEREST_LABELS.get(key, key), color=palette["text"]))
            interests_controls.append(slider)

        filter_controls: list[ft.Control] = []
        for key in FILTER_KEYS:
            filter_controls.append(filter_active[key])
            filter_controls.append(ft.Text("Diferenca maxima permitida", color=palette["muted"]))
            filter_controls.append(filter_delta[key])

        body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                panel(
                    ft.Column(
                        controls=[
                            section_title("Dados publicos"),
                            display_name,
                            bio,
                            ft.ElevatedButton(
                                "Salvar perfil",
                                icon=ft.Icons.SAVE,
                                on_click=save_basic,
                                style=ft.ButtonStyle(bgcolor=palette["primary"], color="#FFFFFF"),
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Interesses expostos"),
                            *interests_controls,
                            ft.ElevatedButton(
                                "Salvar interesses",
                                icon=ft.Icons.TUNE,
                                on_click=save_interests,
                                style=ft.ButtonStyle(bgcolor=palette["primary"], color="#FFFFFF"),
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Privacidade do perfil"),
                            *visibility_checks.values(),
                            ft.ElevatedButton(
                                "Salvar privacidade",
                                icon=ft.Icons.VISIBILITY,
                                on_click=save_visibility,
                            ),
                        ]
                    )
                ),
                panel(
                    ft.Column(
                        controls=[
                            section_title("Filtros de valores"),
                            *filter_controls,
                            ft.ElevatedButton(
                                "Salvar filtros",
                                icon=ft.Icons.FILTER_ALT,
                                on_click=save_filters,
                            ),
                            status,
                        ]
                    )
                ),
            ],
        )
        shell("Controle sobre dados, interesses e exposicao", "profile", body)

    def render_settings() -> None:
        palette = colors()
        profile = api_request("GET", "/profile")
        theme_switch = ft.Switch(label="Dark mode", value=profile.get("theme_mode") == "dark")
        font_slider = ft.Slider(
            min=0.8,
            max=1.6,
            divisions=8,
            value=float(profile.get("chat_font_scale", 1.0)),
            label="{value}",
        )
        export_text = ft.Text("", selectable=True, color=palette["muted"])
        status = ft.Text("", color=palette["muted"])

        def save_settings(_: Any) -> None:
            try:
                updated = api_request(
                    "PATCH",
                    "/profile",
                    {
                        "theme_mode": "dark" if theme_switch.value else "light",
                        "chat_font_scale": font_slider.value,
                    },
                )
                state["profile"] = updated
                state["theme_mode"] = updated.get("theme_mode", "light")
                status.value = "Ajustes salvos."
                render_settings()
            except Exception as exc:
                status.value = str(exc)
                page.update()

        def export_data(_: Any) -> None:
            try:
                data = api_request("GET", "/profile/export")
                export_text.value = str(data)
            except Exception as exc:
                export_text.value = str(exc)
            page.update()

        def delete_data(_: Any) -> None:
            try:
                data = api_request("DELETE", "/profile")
                status.value = data.get("mensagem", "Dados apagados.")
                load_profile()
            except Exception as exc:
                status.value = str(exc)
            page.update()

        body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                panel(
                    ft.Column(
                        controls=[
                            section_title("Conforto visual"),
                            theme_switch,
                            ft.Text("Tamanho da fonte do chat", color=palette["muted"]),
                            font_slider,
                            ft.ElevatedButton(
                                "Salvar ajustes",
                                icon=ft.Icons.SAVE,
                                on_click=save_settings,
                                style=ft.ButtonStyle(bgcolor=palette["primary"], color="#FFFFFF"),
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
                                    ft.OutlinedButton(
                                        "Exportar dados",
                                        icon=ft.Icons.DOWNLOAD,
                                        on_click=export_data,
                                    ),
                                    ft.ElevatedButton(
                                        "Apagar perfil",
                                        icon=ft.Icons.DELETE,
                                        on_click=delete_data,
                                        style=ft.ButtonStyle(bgcolor=palette["primary"], color="#FFFFFF"),
                                    ),
                                ]
                            ),
                            export_text,
                        ]
                    )
                ),
            ],
        )
        shell("Dark mode, fonte do chat e dados", "settings", body)

    try:
        saved_token = page.client_storage.get("matchai_token")
    except Exception:
        saved_token = None

    if saved_token:
        state["token"] = saved_token
        try:
            load_profile()
            render_onboarding()
        except Exception:
            render_login()
    else:
        render_login()


if __name__ == "__main__":
    ft.app(target=main)

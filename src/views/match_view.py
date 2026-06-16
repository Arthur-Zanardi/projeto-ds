import asyncio

import flet as ft

from src.services.api_client import (
    carregar_perfil_publico,
    criar_perfil_mock,
    dar_match,
    registrar_acao_match,
)
from src.services.profile_completion import campos_faltantes_perfil, perfil_publico_completo
from src.services.user_context import usuario_eh_admin
from src.views.app_layout import (
    BG_MUTED,
    BORDER,
    CORAL,
    PINK,
    TEXT_MAIN,
    TEXT_MUTED,
    authenticated_view,
)


PERFIL_PADRAO = {
    "id": "perfil_padrao",
    "match_id": "perfil_padrao",
    "nome": "Seu Match",
    "idade": None,
    "localizacao": "Perto de voce",
    "cargo": "Perfil em descoberta",
    "descricao": "Continue a entrevista para encontrar perfis com mais sintonia.",
    "imagem": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=900&h=1200&fit=crop",
    "sugestoes_inicio": [],
}

ROTULOS_CAMPOS_PERFIL = {
    "nome": "nome",
    "idade": "idade",
    "foto_url": "foto",
    "localizacao": "cidade",
    "cargo": "ocupacao",
    "descricao": "bio",
}


def texto_campos_faltantes(campos: list[str]) -> str:
    if not campos:
        return ""
    return "Falta completar: " + ", ".join(
        ROTULOS_CAMPOS_PERFIL.get(campo, campo)
        for campo in campos
    )


def copiar_perfil(perfil: dict):
    copia = dict(perfil or {})
    copia["sugestoes_inicio"] = list(copia.get("sugestoes_inicio") or [])
    return copia


def montar_perfil_match(match_result):
    if not match_result:
        return copiar_perfil(PERFIL_PADRAO)

    dados_match = match_result.get("dados_match") or {}
    perfil = {**copiar_perfil(PERFIL_PADRAO), **dados_match, **match_result}
    match_id = (
        perfil.get("match_id")
        or perfil.get("id")
        or perfil.get("usuario")
        or PERFIL_PADRAO["id"]
    )

    if isinstance(match_id, int) and dados_match.get("match_id"):
        match_id = dados_match["match_id"]

    perfil["id"] = str(match_id)
    perfil["match_id"] = str(match_id)
    perfil["nome"] = perfil.get("nome") or "Seu Match"
    perfil["imagem"] = (
        perfil.get("imagem")
        or perfil.get("foto_url")
        or PERFIL_PADRAO["imagem"]
    )
    perfil["idade"] = perfil.get("idade")
    perfil["descricao"] = perfil.get("descricao") or PERFIL_PADRAO["descricao"]
    perfil["localizacao"] = perfil.get("localizacao") or ""
    perfil["cargo"] = perfil.get("cargo") or ""
    perfil["sugestoes_inicio"] = list(
        perfil.get("sugestoes_inicio")
        or perfil.get("sugestoes")
        or []
    )
    perfil.pop("afinidade", None)
    return perfil


def perfil_para_payload(perfil: dict):
    match_id = perfil.get("id") or perfil.get("match_id")
    payload = dict(perfil)
    payload.update({
        "id": match_id,
        "match_id": match_id,
        "nome": perfil.get("nome", "Seu Match"),
    })
    payload.pop("afinidade", None)
    return payload


def matchView(page):
    usuario_logado = getattr(page, "usuario_logado", None)
    email_usuario = usuario_logado.get("email") if isinstance(usuario_logado, dict) else None
    is_admin = usuario_eh_admin(email_usuario)
    perfil_cache = getattr(page, "perfil_publico", None)

    state = {
        "candidatos": [
            montar_perfil_match(item)
            for item in (getattr(page, "match_deck", None) or [])
        ],
        "index": 0,
        "carregando": False,
        "confirmado": None,
        "sugestoes": [],
        "perfil_completo": (
            perfil_publico_completo(perfil_cache)
            if isinstance(perfil_cache, dict)
            else None
        ),
        "campos_faltantes": (
            campos_faltantes_perfil(perfil_cache)
            if isinstance(perfil_cache, dict)
            else []
        ),
    }

    if not state["candidatos"] and getattr(page, "match_result", None):
        state["candidatos"].append(montar_perfil_match(page.match_result))

    status_text = ft.Text("", size=12, color=TEXT_MUTED)
    deck_area = ft.Container(expand=True)
    confirm_switcher = ft.AnimatedSwitcher(
        content=ft.Container(),
        duration=350,
        reverse_duration=250,
        transition=ft.AnimatedSwitcherTransition.SCALE,
    )

    nome_field = ft.TextField(label="Nome", border_radius=12)
    idade_field = ft.TextField(label="Idade", border_radius=12)
    localizacao_field = ft.TextField(label="Localizacao", border_radius=12)
    cargo_field = ft.TextField(label="O que faz", border_radius=12)
    descricao_field = ft.TextField(
        label="Descricao",
        multiline=True,
        min_lines=3,
        max_lines=4,
        border_radius=12,
    )
    idade_field.expand = True
    cargo_field.expand = True

    def set_status(mensagem, color=TEXT_MUTED):
        status_text.value = mensagem
        status_text.color = color
        try:
            status_text.update()
        except (AssertionError, RuntimeError):
            pass

    def candidato_atual():
        if state["index"] >= len(state["candidatos"]):
            return None
        return state["candidatos"][state["index"]]

    def abrir_conversa(perfil):
        page.active_match_id = perfil.get("id") or perfil.get("match_id")
        page.match_result = perfil_para_payload(perfil)
        page.active_match_payload = perfil_para_payload(perfil)
        page.match_sugestoes = state.get("sugestoes", [])
        page.go("/chatmatch")

    def avancar():
        state["index"] += 1
        render()

    async def atualizar_status_perfil():
        perfil = await carregar_perfil_publico(usuario_logado)
        if perfil is not None:
            page.perfil_publico = perfil

        state["perfil_completo"] = perfil_publico_completo(perfil)
        state["campos_faltantes"] = campos_faltantes_perfil(perfil)

        if not state["perfil_completo"]:
            set_status("Complete seu perfil antes de descobrir matches.", ft.Colors.RED_500)
        elif not state["candidatos"]:
            set_status("Perfil completo. Busque perfis para comecar.")

        render()
        return state["perfil_completo"]

    async def buscar_deck_async():
        state["carregando"] = True
        set_status("Buscando perfis...")
        render()

        perfil_ok = await atualizar_status_perfil()
        if not perfil_ok:
            state["carregando"] = False
            render()
            return

        resultado = await dar_match([], usuario_logado)
        state["carregando"] = False

        if resultado.get("sucesso"):
            state["candidatos"] = [
                montar_perfil_match(item)
                for item in resultado.get("matches", [])
            ]
            state["index"] = 0
            page.match_deck = [perfil_para_payload(item) for item in state["candidatos"]]
            set_status("Arraste para os lados ou use os botoes.", CORAL)
        elif resultado.get("perfil_incompleto"):
            state["perfil_completo"] = False
            state["campos_faltantes"] = resultado.get("campos_faltantes", [])
            set_status(resultado.get("mensagem", "Complete seu perfil."), ft.Colors.RED_500)
        else:
            set_status(resultado.get("mensagem", "Nenhum perfil encontrado."), ft.Colors.RED_500)

        render()

    def buscar_deck(_=None):
        if hasattr(page, "run_task"):
            page.run_task(buscar_deck_async)
        else:
            asyncio.get_running_loop().create_task(buscar_deck_async())

    def verificar_perfil_inicial():
        if hasattr(page, "run_task"):
            page.run_task(atualizar_status_perfil)
        else:
            asyncio.get_running_loop().create_task(atualizar_status_perfil())

    async def registrar_acao_async(perfil, acao):
        set_status("Registrando escolha...")
        resultado = await registrar_acao_match(perfil["id"], acao, usuario_logado)

        if not resultado.get("sucesso"):
            set_status(resultado.get("mensagem", "Nao foi possivel registrar."), ft.Colors.RED_500)
            return

        if acao == "pass":
            set_status(f"{perfil['nome']} foi removido do deck.")
            avancar()
            return

        if resultado.get("match_confirmado"):
            match_salvo = montar_perfil_match(resultado.get("match") or perfil)
            sugestoes = resultado.get("sugestoes", [])
            match_salvo["sugestoes_inicio"] = sugestoes
            state["confirmado"] = match_salvo
            state["sugestoes"] = sugestoes
            page.match_result = perfil_para_payload(match_salvo)
            page.active_match_id = match_salvo["id"]
            page.match_sugestoes = sugestoes
            set_status("Match confirmado.", CORAL)
            render_confirmacao()
            return

        set_status(resultado.get("mensagem", "Like salvo. Aguardando a outra pessoa."), CORAL)
        avancar()

    def registrar_acao(perfil, acao):
        if hasattr(page, "run_task"):
            page.run_task(registrar_acao_async, perfil, acao)
        else:
            asyncio.get_running_loop().create_task(registrar_acao_async(perfil, acao))

    def background_swipe(texto, icon, color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=ft.Colors.WHITE, size=30),
                    ft.Text(texto, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=18),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            bgcolor=color,
            border_radius=22,
            alignment=ft.Alignment(0, 0),
        )

    def render_card(perfil):
        nome_idade = perfil["nome"]
        if perfil.get("idade"):
            nome_idade = f"{perfil['nome']}, {perfil['idade']}"

        card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src=perfil["imagem"],
                            fit=ft.BoxFit.COVER,
                            width=float("inf"),
                            height=330,
                        ),
                        border_radius=22,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(nome_idade, size=28, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ft.Text(
                                    " • ".join(
                                        item
                                        for item in [perfil.get("localizacao"), perfil.get("cargo")]
                                        if item
                                    ),
                                    size=13,
                                    color=TEXT_MUTED,
                                ),
                                ft.Text(perfil.get("descricao", ""), size=14, color=TEXT_MAIN),
                                ft.Row(
                                    controls=[
                                        ft.FilledButton(
                                            content="Recusar",
                                            icon=ft.Icons.CLOSE,
                                            on_click=lambda _, p=perfil: registrar_acao(p, "pass"),
                                            style=ft.ButtonStyle(
                                                bgcolor="#111827",
                                                color=ft.Colors.WHITE,
                                            ),
                                            expand=True,
                                        ),
                                        ft.FilledButton(
                                            content="Dar match",
                                            icon=ft.Icons.FAVORITE,
                                            on_click=lambda _, p=perfil: registrar_acao(p, "like"),
                                            style=ft.ButtonStyle(
                                                bgcolor=PINK,
                                                color=ft.Colors.WHITE,
                                            ),
                                            expand=True,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                            ],
                            spacing=12,
                        ),
                        padding=18,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=24,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=18, color=ft.Colors.BLACK_12),
        )

        def on_dismiss(event, p=perfil):
            if event.direction == ft.DismissDirection.START_TO_END:
                registrar_acao(p, "like")
            else:
                registrar_acao(p, "pass")

        return ft.Dismissible(
            content=card,
            background=background_swipe("Dar match", ft.Icons.FAVORITE, PINK),
            secondary_background=background_swipe("Recusar", ft.Icons.CLOSE, "#111827"),
            dismiss_direction=ft.DismissDirection.HORIZONTAL,
            dismiss_thresholds={ft.DismissDirection.HORIZONTAL: 0.28},
            on_dismiss=on_dismiss,
        )

    def render_profile_gate():
        faltantes = texto_campos_faltantes(state.get("campos_faltantes", []))
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.LOCK_PERSON, color=ft.Colors.WHITE, size=34),
                        width=72,
                        height=72,
                        border_radius=36,
                        gradient=ft.LinearGradient(colors=[CORAL, PINK]),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(
                        "Complete seu perfil",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_MAIN,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "As perguntas de perfil liberam sua descoberta e deixam seu card pronto para outras pessoas.",
                        size=14,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        faltantes,
                        size=12,
                        color=ft.Colors.RED_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        content="Completar perfil",
                        icon=ft.Icons.PERSON,
                        on_click=lambda _: page.go("/profile"),
                        style=ft.ButtonStyle(bgcolor=CORAL, color=ft.Colors.WHITE),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=14,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=24,
            padding=24,
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    def render_empty():
        if state.get("perfil_completo") is False:
            return render_profile_gate()

        mensagem = (
            "Buscando perfis..."
            if state["carregando"]
            else "Nenhum perfil no deck agora. Converse mais com a IA ou busque novamente."
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.FAVORITE_BORDER, size=54, color=PINK),
                    ft.Text(mensagem, text_align=ft.TextAlign.CENTER, color=TEXT_MUTED),
                    ft.FilledButton(
                        content="Buscar perfis",
                        icon=ft.Icons.TRAVEL_EXPLORE,
                        on_click=buscar_deck,
                        style=ft.ButtonStyle(bgcolor=CORAL, color=ft.Colors.WHITE),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=14,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    def render_confirmacao():
        perfil = state["confirmado"]
        if not perfil:
            confirm_switcher.content = ft.Container()
            return

        sugestoes_controls = []
        for sugestao in state.get("sugestoes", []):
            texto = sugestao.get("texto", "")
            sugestoes_controls.append(
                ft.Container(
                    content=ft.Text(texto, size=13, color=TEXT_MAIN),
                    bgcolor=BG_MUTED,
                    border=ft.Border.all(1, BORDER),
                    border_radius=12,
                    padding=12,
                    on_click=lambda _, t=texto, p=perfil: abrir_conversa_com_sugestao(p, t),
                )
            )

        if not sugestoes_controls:
            sugestoes_controls.append(
                ft.Container(
                    content=ft.Text(
                        "Oi, gostei do nosso match. Quero saber mais sobre voce.",
                        size=13,
                        color=TEXT_MAIN,
                    ),
                    bgcolor=BG_MUTED,
                    border=ft.Border.all(1, BORDER),
                    border_radius=12,
                    padding=12,
                )
            )

        confirm_switcher.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.WHITE, size=38),
                        width=78,
                        height=78,
                        border_radius=39,
                        gradient=ft.LinearGradient(colors=[CORAL, PINK]),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text("Match confirmado", size=24, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text(
                        f"Voce e {perfil['nome']} podem conversar agora.",
                        size=14,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text("Comece com uma destas ideias:", size=13, color=TEXT_MUTED),
                    *sugestoes_controls,
                    ft.Row(
                        controls=[
                            ft.TextButton(
                                content="Continuar vendo perfis",
                                icon=ft.Icons.ARROW_FORWARD,
                                on_click=lambda _: fechar_confirmacao(),
                                style=ft.ButtonStyle(color=TEXT_MUTED),
                            ),
                            ft.FilledButton(
                                content="Abrir conversa",
                                icon=ft.Icons.CHAT_BUBBLE,
                                on_click=lambda _, p=perfil: abrir_conversa(p),
                                style=ft.ButtonStyle(bgcolor=PINK, color=ft.Colors.WHITE),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=24,
            padding=18,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.Colors.BLACK_12),
        )
        try:
            confirm_switcher.update()
        except (AssertionError, RuntimeError):
            pass

    def abrir_conversa_com_sugestao(perfil, sugestao):
        page.pending_starter_message = sugestao
        abrir_conversa(perfil)

    def fechar_confirmacao():
        state["confirmado"] = None
        state["sugestoes"] = []
        avancar()
        render_confirmacao()

    async def adicionar_mock_async(payload):
        set_status("Criando perfil mock...")
        resultado = await criar_perfil_mock(payload, usuario_logado)

        if not resultado.get("sucesso"):
            set_status(resultado.get("mensagem", "Nao foi possivel criar mock."), ft.Colors.RED_500)
            return

        perfil = montar_perfil_match(resultado.get("perfil"))
        state["candidatos"].insert(state["index"], perfil)
        page.match_deck = [perfil_para_payload(item) for item in state["candidatos"]]
        set_status(f"{perfil['nome']} entrou no deck.", CORAL)

        for field in (nome_field, idade_field, localizacao_field, cargo_field, descricao_field):
            field.value = ""

        render()

    def adicionar_perfil(_):
        if not is_admin:
            set_status("Apenas administradores podem criar perfis mock.", ft.Colors.RED_500)
            return

        nome = (nome_field.value or "").strip()
        if not nome:
            set_status("Preencha pelo menos o nome do perfil.", ft.Colors.RED_500)
            return

        payload = {
            "nome": nome,
            "idade": (idade_field.value or "").strip() or None,
            "localizacao": (localizacao_field.value or "").strip(),
            "cargo": (cargo_field.value or "").strip(),
            "descricao": (descricao_field.value or "Perfil mock criado para testar matches.").strip(),
        }

        if hasattr(page, "run_task"):
            page.run_task(adicionar_mock_async, payload)
        else:
            asyncio.get_running_loop().create_task(adicionar_mock_async(payload))

    def render_formulario_custom():
        if not is_admin:
            return ft.Container()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_ADD, color=CORAL, size=20),
                            ft.Text("Adicionar perfil mock", size=16, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "Crie nome, idade e descricao para testar matches.",
                        size=12,
                        color=TEXT_MUTED,
                    ),
                    nome_field,
                    ft.Row([idade_field, cargo_field], spacing=10),
                    localizacao_field,
                    descricao_field,
                    ft.FilledButton(
                        content="Adicionar mock",
                        icon=ft.Icons.ADD,
                        on_click=adicionar_perfil,
                        style=ft.ButtonStyle(bgcolor=CORAL, color=ft.Colors.WHITE),
                    ),
                ],
                spacing=10,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=18,
            padding=16,
        )

    def render():
        perfil = candidato_atual()
        deck_area.content = render_card(perfil) if perfil else render_empty()
        render_confirmacao()
        try:
            deck_area.update()
        except (AssertionError, RuntimeError):
            pass
        try:
            page.update()
        except (AssertionError, RuntimeError):
            pass

    content = ft.ListView(
        expand=True,
        padding=ft.Padding(16, 8, 16, 18),
        spacing=14,
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text("Descobrir perfis", size=24, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ft.Text(
                                    "Arraste para a direita para dar match ou para a esquerda para recusar.",
                                    size=13,
                                    color=TEXT_MUTED,
                                ),
                            ],
                            expand=True,
                            spacing=4,
                        ),
                        ft.FilledButton(
                            content="Buscar perfis",
                            icon=ft.Icons.TRAVEL_EXPLORE,
                            on_click=buscar_deck,
                            style=ft.ButtonStyle(bgcolor=CORAL, color=ft.Colors.WHITE),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, BORDER),
                border_radius=18,
                padding=16,
            ),
            status_text,
            deck_area,
            confirm_switcher,
            render_formulario_custom(),
        ],
    )

    if state.get("perfil_completo") is False:
        set_status("Complete seu perfil antes de descobrir matches.", ft.Colors.RED_500)
    elif not state["candidatos"]:
        set_status("Use Buscar perfis ou venha pelo botao Dar match da entrevista.")
    else:
        set_status("Arraste para os lados ou use os botoes.", CORAL)

    render()
    if state.get("perfil_completo") is None:
        verificar_perfil_inicial()

    return authenticated_view(
        page,
        "/match",
        "Descobrir",
        content,
        subtitle="Matches reais so abrem conversa quando os dois curtirem.",
    )

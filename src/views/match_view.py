import asyncio
import re
import uuid

import flet as ft

from src.services.api_client import criar_match, listar_matches
from src.services.user_context import usuario_eh_admin


CORAL = "#FF7F50"
PINK = "#FF69B4"
BG_MAIN = "#FAFAFA"
BG_MUTED = "#F3F4F6"
TEXT_MAIN = "#111827"
TEXT_MUTED = "#6B7280"
BORDER = "#E5E7EB"


PERFIS_MOCK = {
    "user_maria": {
        "id": "user_maria",
        "nome": "Maria",
        "idade": 22,
        "localizacao": "Recife, PE",
        "cargo": "Estudante de Tecnologia",
        "descricao": (
            "Curiosa por tecnologia, cafeterias escondidas e conversas que "
            "pulam de animes para planos de viagem sem pedir licenca."
        ),
        "tracos": ["Comunicativa", "Criativa", "Aventureira"],
        "afinidade": "92%",
        "imagem": (
            "https://images.unsplash.com/photo-1494790108377-be9c29b29330"
            "?w=900&h=1200&fit=crop"
        ),
        "respostas": [
            "Eu topo muito esse assunto. Me conta mais do seu jeito de viver isso.",
            "Gostei da energia. Acho que a gente teria uma conversa longa sobre isso.",
            "Isso combina comigo tambem, principalmente quando vira plano espontaneo.",
        ],
    },
    "user_carmen": {
        "id": "user_carmen",
        "nome": "Carmen",
        "idade": 24,
        "localizacao": "Olinda, PE",
        "cargo": "Designer",
        "descricao": (
            "Designer tranquila, apaixonada por musica, cozinhar no fim de "
            "semana e encontrar beleza nas pequenas rotinas."
        ),
        "tracos": ["Carinhosa", "Tranquila", "Caseira"],
        "afinidade": "86%",
        "imagem": (
            "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91"
            "?w=900&h=1200&fit=crop"
        ),
        "respostas": [
            "Amei a calma disso. Acho bonito quando a conversa nao precisa correr.",
            "Isso tem muito a ver comigo. Eu perguntaria mil detalhes pessoalmente.",
            "Gostei. Me parece o tipo de coisa que vira lembranca boa.",
        ],
    },
    "user_lia": {
        "id": "user_lia",
        "nome": "Lia",
        "idade": 21,
        "localizacao": "Joao Pessoa, PB",
        "cargo": "Fotografa",
        "descricao": (
            "Fotografa de rua, fa de trilhas curtas, playlists enormes e "
            "gente que sabe rir de um dia estranho."
        ),
        "tracos": ["Espontanea", "Observadora", "Bem-humorada"],
        "afinidade": "89%",
        "imagem": (
            "https://images.unsplash.com/photo-1517841905240-472988babdf9"
            "?w=900&h=1200&fit=crop"
        ),
        "respostas": [
            "Isso daria uma foto mental muito boa. Curti demais.",
            "Me ganhou no detalhe. Eu gosto quando alguem presta atencao assim.",
            "Esse papo tem cara de render uma caminhada sem ver o tempo passar.",
        ],
    },
}


PERFIL_PADRAO = {
    "id": "user_beatriz",
    "nome": "Beatriz Lima",
    "idade": 19,
    "localizacao": "Recife, PE",
    "cargo": "Product Designer",
    "descricao": (
        "Alma criativa apaixonada por fotografia e conversas sinceras. "
        "Procura conexoes leves, curiosas e emocionalmente presentes."
    ),
    "tracos": ["Empatica", "Criativa", "Aventureira"],
    "afinidade": "88%",
    "imagem": (
        "https://images.unsplash.com/photo-1524504388940-b1c1722653e1"
        "?w=900&h=1200&fit=crop"
    ),
    "respostas": [
        "Que gostoso ler isso. Me conta como isso aparece no seu dia a dia.",
        "Acho que essa conversa ja comecou bem.",
        "Curti. Tem um jeito bem verdadeiro nesse assunto.",
    ],
}


def copiar_perfil(perfil: dict):
    copia = dict(perfil)
    copia["tracos"] = list(perfil.get("tracos", []))
    copia["respostas"] = list(perfil.get("respostas", []))
    return copia


def obter_perfis_mock(page):
    if not hasattr(page, "perfis_mock_personalizados"):
        page.perfis_mock_personalizados = {
            perfil_id: copiar_perfil(perfil)
            for perfil_id, perfil in PERFIS_MOCK.items()
        }

    return page.perfis_mock_personalizados


def montar_perfil_match(match_result):
    if not match_result:
        return copiar_perfil(PERFIL_PADRAO)

    match_id = (
        match_result.get("match_id")
        or match_result.get("id")
        or match_result.get("usuario")
    )
    perfil = {
        **copiar_perfil(PERFIL_PADRAO),
        **copiar_perfil(PERFIS_MOCK.get(match_id, {})),
    }
    dados_match = match_result.get("dados_match") or {}
    perfil.update(dados_match)
    perfil.update({k: v for k, v in match_result.items() if v is not None})

    perfil["id"] = match_id or perfil["id"]
    perfil["match_id"] = perfil["id"]
    perfil["nome"] = match_result.get("nome") or perfil["nome"]
    perfil["afinidade"] = match_result.get("afinidade") or perfil.get("afinidade")
    perfil["idade"] = int(perfil.get("idade") or PERFIL_PADRAO["idade"])
    perfil["tracos"] = list(perfil.get("tracos") or PERFIL_PADRAO["tracos"])
    perfil["respostas"] = list(perfil.get("respostas") or PERFIL_PADRAO["respostas"])
    return perfil


def perfil_para_payload(perfil: dict):
    match_id = perfil.get("id") or perfil.get("match_id")
    return {
        **perfil,
        "id": match_id,
        "match_id": match_id,
        "nome": perfil.get("nome", "Seu Match"),
        "afinidade": perfil.get("afinidade"),
    }


def slugify(texto: str):
    slug = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")
    return slug or "perfil"


def matchView(page):
    usuario_logado = getattr(page, "usuario_logado", None)
    email_usuario = (
        usuario_logado.get("email")
        if isinstance(usuario_logado, dict)
        else None
    )
    is_admin = usuario_eh_admin(email_usuario)
    perfis = obter_perfis_mock(page)
    match_inicial = montar_perfil_match(getattr(page, "match_result", None))
    selected_id = match_inicial.get("id")

    if selected_id not in perfis:
        perfis[selected_id] = match_inicial

    state = {
        "aba": getattr(page, "match_active_tab", "perfis"),
        "selected_id": selected_id,
        "matches_salvos": [],
        "carregando_matches": True,
    }

    status_text = ft.Text("", size=12, color=TEXT_MUTED)
    tab_bar = ft.Container()
    content_area = ft.Container(expand=True)

    nome_field = ft.TextField(label="Nome", border_radius=12)
    idade_field = ft.TextField(label="Idade", border_radius=12)
    foto_field = ft.TextField(label="URL da foto", border_radius=12)
    localizacao_field = ft.TextField(label="Localizacao", border_radius=12)
    cargo_field = ft.TextField(label="O que faz", border_radius=12)
    afinidade_field = ft.TextField(label="Afinidade", border_radius=12)
    tracos_field = ft.TextField(
        label="Tracos separados por virgula",
        border_radius=12,
    )
    descricao_field = ft.TextField(
        label="Descricao",
        multiline=True,
        min_lines=3,
        max_lines=4,
        border_radius=12,
    )

    def set_status(mensagem, color=TEXT_MUTED):
        status_text.value = mensagem
        status_text.color = color
        try:
            status_text.update()
        except AssertionError:
            pass

    def perfil_atual():
        return perfis.get(state["selected_id"], copiar_perfil(PERFIL_PADRAO))

    def trocar_aba(aba):
        state["aba"] = aba
        page.match_active_tab = aba
        render()

    def selecionar_perfil(perfil_id):
        state["selected_id"] = perfil_id
        page.match_result = perfil_para_payload(perfis[perfil_id])
        render()

    def ir_chat(perfil):
        page.active_match_id = perfil.get("id") or perfil.get("match_id")
        page.match_result = perfil_para_payload(perfil)
        page.go("/chatmatch")

    def render_tab_button(label, icon, aba):
        selecionado = state["aba"] == aba
        button_cls = ft.FilledButton if selecionado else ft.TextButton
        style = ft.ButtonStyle(
            bgcolor=CORAL if selecionado else ft.Colors.TRANSPARENT,
            color=ft.Colors.WHITE if selecionado else TEXT_MUTED,
        )
        return button_cls(
            content=label,
            icon=icon,
            on_click=lambda _: trocar_aba(aba),
            style=style,
            expand=True,
        )

    def render_tabs():
        tab_bar.content = ft.Container(
            content=ft.Row(
                controls=[
                    render_tab_button("Perfis", ft.Icons.FAVORITE, "perfis"),
                    render_tab_button(
                        "Conversas",
                        ft.Icons.CHAT_BUBBLE_OUTLINE,
                        "conversas",
                    ),
                ],
                spacing=0,
            ),
            bgcolor=BG_MUTED,
            border_radius=14,
            padding=4,
        )

    def chip_perfil(perfil):
        selecionado = perfil["id"] == state["selected_id"]
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src=perfil["imagem"],
                            fit=ft.BoxFit.COVER,
                            width=38,
                            height=38,
                        ),
                        width=38,
                        height=38,
                        border_radius=19,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                perfil["nome"],
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=TEXT_MAIN,
                            ),
                            ft.Text(
                                perfil.get("afinidade", "Mock"),
                                size=11,
                                color=TEXT_MUTED,
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                spacing=8,
            ),
            padding=10,
            border_radius=16,
            bgcolor=ft.Colors.WHITE if selecionado else BG_MUTED,
            border=ft.border.all(1, CORAL if selecionado else BORDER),
            on_click=lambda _, perfil_id=perfil["id"]: selecionar_perfil(perfil_id),
        )

    def render_lista_perfis():
        return ft.ListView(
            controls=[chip_perfil(perfil) for perfil in perfis.values()],
            horizontal=True,
            spacing=10,
            height=76,
            padding=ft.padding.only(left=2, right=2),
        )

    def render_tracos(perfil):
        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(trait, size=12, color=TEXT_MAIN),
                    bgcolor=BG_MUTED,
                    border=ft.border.all(1, BORDER),
                    border_radius=18,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                )
                for trait in perfil.get("tracos", [])
            ],
            wrap=True,
            spacing=8,
            run_spacing=8,
        )

    def render_card_perfil(perfil):
        badge = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=PINK, size=16),
                    ft.Text(
                        perfil.get("afinidade") or "Mock",
                        size=12,
                        color=PINK,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=4,
            ),
            top=14,
            right=14,
            bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.WHITE),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=20,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Stack(
                        controls=[
                            ft.Container(
                                content=ft.Image(
                                    src=perfil["imagem"],
                                    fit=ft.BoxFit.COVER,
                                    width=float("inf"),
                                    height=320,
                                ),
                                border_radius=22,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            ),
                            badge,
                        ],
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            f"{perfil['nome']}, {perfil['idade']}",
                                            size=26,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT_MAIN,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                                            icon_color=PINK,
                                            tooltip="Conversar",
                                            on_click=lambda _: salvar_match_e_abrir(
                                                perfil
                                            ),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(
                                    (
                                        f"{perfil.get('localizacao', '')} - "
                                        f"{perfil.get('cargo', '')}"
                                    ),
                                    color=TEXT_MUTED,
                                ),
                                ft.Text(
                                    perfil.get("descricao", ""),
                                    size=14,
                                    color=TEXT_MAIN,
                                ),
                                render_tracos(perfil),
                                ft.Row(
                                    controls=[
                                        ft.TextButton(
                                            content="Pular",
                                            icon=ft.Icons.CLOSE,
                                            on_click=lambda _: proximo_perfil(),
                                            style=ft.ButtonStyle(color=TEXT_MUTED),
                                        ),
                                        ft.FilledButton(
                                            content="Dar match",
                                            icon=ft.Icons.FAVORITE,
                                            on_click=lambda _: salvar_match(perfil),
                                            style=ft.ButtonStyle(
                                                bgcolor=PINK,
                                                color=ft.Colors.WHITE,
                                            ),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
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
            border_radius=24,
            border=ft.border.all(1, BORDER),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=18,
                color=ft.Colors.BLACK12,
            ),
        )

    def proximo_perfil():
        ids = list(perfis.keys())
        indice = ids.index(state["selected_id"])
        selecionar_perfil(ids[(indice + 1) % len(ids)])

    def adicionar_perfil(_):
        if not is_admin:
            set_status(
                "Apenas administradores podem criar perfis mock.",
                ft.Colors.RED_500,
            )
            return

        nome = (nome_field.value or "").strip()
        if not nome:
            set_status("Preencha pelo menos o nome do perfil.", ft.Colors.RED_500)
            return

        try:
            idade = int((idade_field.value or PERFIL_PADRAO["idade"]).strip())
        except ValueError:
            set_status("Idade precisa ser um numero.", ft.Colors.RED_500)
            return

        tracos = [
            traco.strip()
            for traco in (tracos_field.value or "").split(",")
            if traco.strip()
        ] or ["Personalizado", "Curioso", "Disponivel"]

        descricao = (descricao_field.value or "").strip()
        perfil_id = f"custom_{slugify(nome)}_{uuid.uuid4().hex[:6]}"
        novo_perfil = {
            "id": perfil_id,
            "match_id": perfil_id,
            "nome": nome,
            "idade": idade,
            "localizacao": (
                localizacao_field.value or PERFIL_PADRAO["localizacao"]
            ).strip(),
            "cargo": (cargo_field.value or "Perfil personalizado").strip(),
            "descricao": descricao or "Perfil mock criado para testar matches.",
            "tracos": tracos,
            "afinidade": (afinidade_field.value or "94%").strip(),
            "imagem": (foto_field.value or PERFIL_PADRAO["imagem"]).strip(),
            "mock_customizado": True,
            "respostas": [
                "Gostei desse comeco. Me conta mais sobre voce.",
                "Esse assunto combina com o perfil que voce montou para mim.",
                "Curti a pergunta. Eu responderia isso com calma num cafe.",
            ],
        }

        perfis[perfil_id] = novo_perfil
        state["selected_id"] = perfil_id
        page.match_result = perfil_para_payload(novo_perfil)

        for field in (
            nome_field,
            idade_field,
            foto_field,
            localizacao_field,
            cargo_field,
            afinidade_field,
            tracos_field,
            descricao_field,
        ):
            field.value = ""

        set_status(f"Perfil {nome} adicionado aos mocks.", CORAL)
        render()

    def render_formulario_custom():
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_ADD, color=CORAL, size=20),
                            ft.Text(
                                "Adicionar perfil mock",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "Crie nomes, idades, fotos e descricoes para testar matches.",
                        size=12,
                        color=TEXT_MUTED,
                    ),
                    nome_field,
                    ft.Row(
                        controls=[idade_field, afinidade_field],
                        spacing=10,
                    ),
                    foto_field,
                    ft.Row(
                        controls=[localizacao_field, cargo_field],
                        spacing=10,
                    ),
                    tracos_field,
                    descricao_field,
                    ft.FilledButton(
                        content="Adicionar mock",
                        icon=ft.Icons.ADD,
                        on_click=adicionar_perfil,
                        style=ft.ButtonStyle(
                            bgcolor=CORAL,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
                spacing=10,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, BORDER),
            border_radius=18,
            padding=16,
        )

    async def salvar_match_async(perfil, abrir_chat=False):
        set_status(f"Salvando match com {perfil['nome']}...")
        resultado = await criar_match(perfil_para_payload(perfil), usuario_logado)

        if not resultado.get("sucesso"):
            set_status(resultado.get("mensagem", "Nao foi possivel salvar."), ft.Colors.RED_500)
            return

        page.match_result = perfil_para_payload(perfil)
        page.active_match_id = perfil["id"]
        set_status(f"Match com {perfil['nome']} salvo no banco.", CORAL)
        await carregar_matches_salvos(renderizar=False)

        if abrir_chat:
            page.go("/chatmatch")
            return

        state["aba"] = "conversas"
        page.match_active_tab = "conversas"
        render()

    def salvar_match(perfil):
        if hasattr(page, "run_task"):
            page.run_task(salvar_match_async, perfil)
        else:
            asyncio.get_running_loop().create_task(salvar_match_async(perfil))

    def salvar_match_e_abrir(perfil):
        if hasattr(page, "run_task"):
            page.run_task(salvar_match_async, perfil, True)
        else:
            asyncio.get_running_loop().create_task(
                salvar_match_async(perfil, True)
            )

    def abrir_conversa(match_salvo):
        perfil = montar_perfil_match(match_salvo)
        page.active_match_id = perfil["id"]
        page.match_result = perfil_para_payload(perfil)
        page.go("/chatmatch")

    def render_match_item(match_salvo):
        perfil = montar_perfil_match(match_salvo)
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src=perfil["imagem"],
                            fit=ft.BoxFit.COVER,
                            width=52,
                            height=52,
                        ),
                        width=52,
                        height=52,
                        border_radius=26,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                perfil["nome"],
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN,
                            ),
                            ft.Text(
                                perfil.get("descricao", "")[:80],
                                size=12,
                                color=TEXT_MUTED,
                            ),
                            ft.Text(
                                perfil.get("afinidade") or "Match salvo",
                                size=11,
                                color=PINK,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                        icon_color=PINK,
                        tooltip="Abrir conversa",
                        on_click=lambda _, match=match_salvo: abrir_conversa(match),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, BORDER),
            border_radius=16,
            padding=12,
        )

    def render_conversas():
        if state["carregando_matches"]:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.ProgressRing(width=24, height=24, color=PINK),
                        ft.Text("Carregando conversas...", color=TEXT_MUTED),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment=ft.Alignment(0, 0),
                padding=30,
            )

        if not state["matches_salvos"]:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.CHAT_BUBBLE_OUTLINE,
                            color=TEXT_MUTED,
                            size=32,
                        ),
                        ft.Text(
                            "Nenhum match salvo ainda.",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_MAIN,
                        ),
                        ft.Text(
                            "Use a aba Perfis para dar match nos mocks.",
                            size=13,
                            color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, BORDER),
                border_radius=18,
                padding=28,
            )

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Conversas salvas",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_MAIN,
                        ),
                        ft.TextButton(
                            content="Atualizar",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda _: carregar_matches(),
                            style=ft.ButtonStyle(color=CORAL),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(
                    controls=[
                        render_match_item(match_salvo)
                        for match_salvo in state["matches_salvos"]
                    ],
                    spacing=10,
                ),
            ],
            spacing=12,
        )

    def render_perfis():
        perfil = perfil_atual()
        controls = [
            render_lista_perfis(),
            render_card_perfil(perfil),
        ]

        if is_admin:
            controls.append(render_formulario_custom())

        return ft.Column(
            controls=controls,
            spacing=16,
        )

    def render(update_page=True):
        render_tabs()
        content_area.content = (
            render_conversas() if state["aba"] == "conversas" else render_perfis()
        )
        if update_page:
            page.update()

    async def carregar_matches_salvos(renderizar=True):
        state["carregando_matches"] = True
        if renderizar:
            render()

        state["matches_salvos"] = await listar_matches(usuario_logado)
        state["carregando_matches"] = False

        if renderizar:
            render()

    def carregar_matches():
        if hasattr(page, "run_task"):
            page.run_task(carregar_matches_salvos)
        else:
            asyncio.get_running_loop().create_task(carregar_matches_salvos())

    def go_back(_):
        page.go("/chat")

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=TEXT_MAIN,
                    on_click=go_back,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Matches",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_MAIN,
                        ),
                        ft.Text(
                            "Perfis mock, matches salvos e conversas.",
                            size=12,
                            color=TEXT_MUTED,
                        ),
                    ],
                    spacing=0,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(top=10, bottom=6),
    )

    view_content = ft.Container(
        content=ft.Column(
            controls=[
                header,
                tab_bar,
                status_text,
                content_area,
            ],
            spacing=12,
        ),
        padding=20,
    )

    render(update_page=False)
    carregar_matches()

    return ft.View(
        route="/match",
        controls=[view_content],
        bgcolor=BG_MAIN,
        scroll=ft.ScrollMode.AUTO,
    )

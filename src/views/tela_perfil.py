import asyncio

import flet as ft

from src.services.api_client import carregar_perfil_publico, salvar_perfil_publico
from src.services.profile_completion import (
    anexar_status_perfil,
    campos_faltantes_perfil,
    perfil_publico_completo,
)
from src.services.profile_images import (
    ALLOWED_PROFILE_IMAGE_EXTENSIONS,
    MAX_PROFILE_IMAGE_BYTES,
    gerar_caminho_upload_imagem,
    validar_imagem_perfil,
)
from src.views.app_layout import (
    BG_MUTED,
    BORDER,
    CORAL,
    PINK,
    TEXT_MAIN,
    TEXT_MUTED,
    authenticated_view,
)


ROTULOS_CAMPOS = {
    "nome": "nome",
    "idade": "idade",
    "foto_url": "foto",
    "localizacao": "cidade",
    "cargo": "ocupacao",
    "descricao": "bio",
}


def _executar_tarefa(page: ft.Page, coroutine, *args):
    if hasattr(page, "run_task"):
        page.run_task(coroutine, *args)
    else:
        asyncio.get_running_loop().create_task(coroutine(*args))


def _texto_faltantes(campos: list[str]) -> str:
    if not campos:
        return "Perfil completo. Voce ja pode descobrir matches."

    nomes = [ROTULOS_CAMPOS.get(campo, campo) for campo in campos]
    return "Falta completar: " + ", ".join(nomes) + "."


def profileView(page: ft.Page) -> ft.View:
    usuario_logado = getattr(page, "usuario_logado", None) or {}
    email_usuario = str(usuario_logado.get("email") or "").strip().lower()

    state = {
        "foto_url": "",
        "upload_destino": "",
        "carregando": True,
    }

    nome_field = ft.TextField(label="Nome", border_radius=12)
    idade_field = ft.TextField(label="Idade", border_radius=12, keyboard_type=ft.KeyboardType.NUMBER)
    localizacao_field = ft.TextField(label="Cidade, estado", border_radius=12)
    cargo_field = ft.TextField(label="O que voce faz", border_radius=12)
    descricao_field = ft.TextField(
        label="Uma bio curta sobre voce",
        multiline=True,
        min_lines=4,
        max_lines=6,
        border_radius=12,
    )
    idade_field.expand = True
    cargo_field.expand = True

    status_text = ft.Text("Carregando perfil...", size=12, color=TEXT_MUTED)
    completion_text = ft.Text("", size=12, color=TEXT_MUTED)
    upload_text = ft.Text("PNG, JPG ou WebP ate 16 MB.", size=12, color=TEXT_MUTED)
    upload_progress = ft.ProgressBar(
        value=0,
        color=PINK,
        bgcolor="#FFE4EC",
        border_radius=8,
        visible=False,
    )

    def avatar_placeholder():
        return ft.Container(
            content=ft.Icon(ft.Icons.PERSON, size=48, color=TEXT_MUTED),
            width=132,
            height=132,
            border_radius=66,
            bgcolor=BG_MUTED,
            alignment=ft.Alignment(0, 0),
        )

    avatar_switcher = ft.AnimatedSwitcher(
        content=avatar_placeholder(),
        duration=300,
        reverse_duration=180,
        transition=ft.AnimatedSwitcherTransition.SCALE,
    )

    def update_avatar():
        foto = str(state.get("foto_url") or "").strip()
        if foto:
            avatar_switcher.content = ft.Container(
                content=ft.Image(
                    src=foto,
                    fit=ft.BoxFit.COVER,
                    width=132,
                    height=132,
                    error_content=avatar_placeholder(),
                ),
                width=132,
                height=132,
                border_radius=66,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                bgcolor=BG_MUTED,
            )
        else:
            avatar_switcher.content = avatar_placeholder()

        try:
            avatar_switcher.update()
        except (AssertionError, RuntimeError):
            pass

    def payload_atual():
        return {
            "nome": (nome_field.value or "").strip(),
            "idade": (idade_field.value or "").strip() or None,
            "foto_url": str(state.get("foto_url") or "").strip(),
            "localizacao": (localizacao_field.value or "").strip(),
            "cargo": (cargo_field.value or "").strip(),
            "descricao": (descricao_field.value or "").strip(),
        }

    def atualizar_completude(perfil=None):
        dados = perfil or payload_atual()
        faltantes = campos_faltantes_perfil(dados)
        completo = not faltantes
        completion_text.value = _texto_faltantes(faltantes)
        completion_text.color = CORAL if completo else ft.Colors.RED_500
        return completo, faltantes

    def preencher(perfil):
        perfil = anexar_status_perfil(perfil or {})
        nome_field.value = perfil.get("nome") or usuario_logado.get("nome", "")
        idade_field.value = "" if perfil.get("idade") is None else str(perfil.get("idade"))
        state["foto_url"] = perfil.get("foto_url") or perfil.get("imagem") or ""
        localizacao_field.value = perfil.get("localizacao") or ""
        cargo_field.value = perfil.get("cargo") or ""
        descricao_field.value = perfil.get("descricao") or ""
        update_avatar()
        atualizar_completude(perfil)

    def set_status(mensagem, color=TEXT_MUTED):
        status_text.value = mensagem
        status_text.color = color
        try:
            status_text.update()
        except (AssertionError, RuntimeError):
            pass

    def set_upload_status(mensagem, color=TEXT_MUTED, progress_visible=False, progress=0):
        upload_text.value = mensagem
        upload_text.color = color
        upload_progress.visible = progress_visible
        upload_progress.value = progress
        try:
            upload_text.update()
            upload_progress.update()
        except (AssertionError, RuntimeError):
            pass

    async def carregar():
        perfil = await carregar_perfil_publico(usuario_logado)
        preencher(perfil)
        state["carregando"] = False
        set_status("Complete seu perfil para liberar a descoberta.", CORAL)
        page.update()

    async def salvar():
        payload = payload_atual()
        completo, faltantes = atualizar_completude(payload)

        if payload["idade"] is not None and not str(payload["idade"]).isdigit():
            set_status("Informe a idade usando apenas numeros.", ft.Colors.RED_500)
            return

        if not completo:
            set_status(_texto_faltantes(faltantes), ft.Colors.RED_500)
            page.update()
            return

        set_status("Salvando perfil...")
        resultado = await salvar_perfil_publico(payload, usuario_logado)

        if resultado.get("sucesso"):
            perfil = anexar_status_perfil(resultado.get("perfil"))
            preencher(perfil)
            page.perfil_publico = perfil
            set_status("Perfil salvo. Descoberta liberada.", CORAL)
        else:
            set_status(resultado.get("mensagem", "Nao foi possivel salvar."), ft.Colors.RED_500)

        page.update()

    def salvar_clicked(_):
        _executar_tarefa(page, salvar)

    def on_upload(event):
        if event.error:
            set_upload_status(f"Falha no envio: {event.error}", ft.Colors.RED_500)
            return

        progresso = float(event.progress or 0)
        if progresso >= 1:
            state["foto_url"] = state.get("upload_destino", "")
            update_avatar()
            atualizar_completude()
            set_upload_status("Foto enviada. Salve o perfil para confirmar.", CORAL)
            page.update()
            return

        set_upload_status("Enviando foto...", TEXT_MUTED, progress_visible=True, progress=progresso)

    file_picker = ft.FilePicker(on_upload=on_upload)
    try:
        if hasattr(page, "overlay") and file_picker not in page.overlay:
            page.overlay.append(file_picker)
    except (AssertionError, RuntimeError, TypeError):
        pass

    async def escolher_foto():
        arquivos = await file_picker.pick_files(
            dialog_title="Escolha uma foto de perfil",
            file_type=ft.FilePickerFileType.IMAGE,
            allowed_extensions=list(ALLOWED_PROFILE_IMAGE_EXTENSIONS),
            allow_multiple=False,
            with_data=False,
        )
        if not arquivos:
            return

        arquivo = arquivos[0]
        valido, mensagem = validar_imagem_perfil(arquivo.name, arquivo.size)
        if not valido:
            set_upload_status(mensagem, ft.Colors.RED_500)
            page.update()
            return

        destino = gerar_caminho_upload_imagem(email_usuario, arquivo.name)
        state["upload_destino"] = destino
        set_upload_status("Preparando envio...", TEXT_MUTED, progress_visible=True, progress=0)
        upload_url = page.get_upload_url(destino, 600)
        await file_picker.upload(
            [
                ft.FilePickerUploadFile(
                    upload_url=upload_url,
                    id=arquivo.id,
                    name=arquivo.name,
                )
            ]
        )

    def escolher_foto_clicked(_):
        _executar_tarefa(page, escolher_foto)

    for field in (nome_field, idade_field, localizacao_field, cargo_field, descricao_field):
        field.on_change = lambda _: (atualizar_completude(), page.update())

    _executar_tarefa(page, carregar)

    image_panel = ft.Container(
        content=ft.Column(
            controls=[
                avatar_switcher,
                ft.FilledButton(
                    content="Selecionar foto",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=escolher_foto_clicked,
                    style=ft.ButtonStyle(bgcolor=PINK, color=ft.Colors.WHITE),
                ),
                upload_text,
                upload_progress,
                ft.Text(
                    f"Limite: {MAX_PROFILE_IMAGE_BYTES // (1024 * 1024)} MB.",
                    size=11,
                    color=TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        bgcolor="#FFF7FA",
        border=ft.Border.all(1, "#FFD3E4"),
        border_radius=18,
        padding=16,
        width=210,
    )

    form_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.EDIT_NOTE, color=CORAL, size=22),
                        ft.Text("Perguntas do perfil", size=18, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    "Esses dados aparecem no seu card de descoberta e liberam seus matches.",
                    size=13,
                    color=TEXT_MUTED,
                ),
                nome_field,
                ft.Row([idade_field, cargo_field], spacing=10),
                localizacao_field,
                descricao_field,
                completion_text,
                status_text,
                ft.Row(
                    controls=[
                        ft.TextButton(
                            content="Ir para descobrir",
                            icon=ft.Icons.FAVORITE,
                            on_click=lambda _: page.go("/match"),
                            style=ft.ButtonStyle(color=PINK),
                        ),
                        ft.FilledButton(
                            content="Salvar perfil",
                            icon=ft.Icons.SAVE,
                            on_click=salvar_clicked,
                            style=ft.ButtonStyle(bgcolor=CORAL, color=ft.Colors.WHITE),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    wrap=True,
                ),
            ],
            spacing=14,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=18,
        padding=18,
        expand=True,
    )

    content = ft.ListView(
        expand=True,
        padding=ft.Padding(18, 10, 18, 18),
        spacing=16,
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Complete seu perfil", size=24, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text(
                            "Cadastro agora e so e-mail e senha. As perguntas ficam aqui.",
                            size=13,
                            color=TEXT_MUTED,
                        ),
                    ],
                    spacing=4,
                ),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, BORDER),
                border_radius=18,
                padding=16,
            ),
            ft.Row(
                controls=[image_panel, form_panel],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
                wrap=True,
            ),
        ],
    )

    return authenticated_view(
        page,
        "/profile",
        "Perfil",
        content,
        subtitle="Complete as perguntas para aparecer bem nos matches.",
    )

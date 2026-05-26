import asyncio

import flet as ft
from src.services.llm_conversation import llm_conversation
from src.services.api_client import carregar_historico, dar_match

def chatView(page):
    mensagens_usuario = []
    
    def goto_profile_screen(e):
        page.go("/profile")

    def create_message_container(remetente, mensagem):
        is_usuario = remetente == "usuario"
        return ft.Container(
            content=ft.Row(
                controls=[ft.Text(f"{mensagem}", size=24)],
                alignment=(
                    ft.CrossAxisAlignment.END
                    if is_usuario
                    else ft.CrossAxisAlignment.START
                ),
                wrap=True,
            ),
            bgcolor=ft.Colors.RED_100 if is_usuario else ft.Colors.BLUE_100,
            padding=12,
            margin=12,
            width=200 if is_usuario else 350,
        )

    def append_message(remetente, mensagem):
        messages_view.controls.append(
            create_message_container(remetente, mensagem)
        )

    def set_match_button_loading(is_loading):
        match_button.disabled = is_loading
        match_button.content = "Buscando..." if is_loading else "Dar match"
        match_button.icon = ft.Icons.HOURGLASS_TOP if is_loading else ft.Icons.FAVORITE
        match_button.update()

    def send_clicked(e):
        texto_usuario = field.value.strip() 
        if not texto_usuario:
            return 

        mensagens_usuario.append(texto_usuario)
        append_message("usuario", texto_usuario)
        
        field.value = "" 
        messages_view.update()
        
       
        recieve_message(texto_usuario) 
    
    def recieve_message(texto_enviado):
        response = llm_conversation(texto_enviado)

        append_message("ia", response)

        messages_view.update()

    async def match_clicked_async():
        set_match_button_loading(True)

        resultado = await dar_match(mensagens_usuario)

        if resultado.get("sucesso"):
            match = resultado["match"]
            texto_match = (
                f"Deu match com {match.get('nome', 'alguem especial')}! "
                f"Afinidade: {match.get('afinidade', 'sem porcentagem')}"
            )

            dimensoes = match.get("dimensoes_comparadas")
            if dimensoes:
                texto_match += f" ({dimensoes} pontos comparados)"
        else:
            texto_match = resultado.get(
                "mensagem",
                "Ainda nao foi possivel encontrar um match.",
            )

        append_message("ia", texto_match)
        messages_view.update()
        set_match_button_loading(False)

    def match_clicked(e):
        if hasattr(page, "run_task"):
            page.run_task(match_clicked_async)
        else:
            try:
                asyncio.get_running_loop().create_task(match_clicked_async())
            except RuntimeError:
                pass

    field = ft.TextField(
        hint_text="Digite aqui a sua mensagem",
        expand=True,
    )

    send_buttom = ft.FilledIconButton(
        icon=ft.Icons.SEND,
        on_click=send_clicked,
        style=ft.ButtonStyle(
            color= "#fff0f3",
            bgcolor= "#ff88ac",)
    )

    match_button = ft.FilledButton(
        content="Dar match",
        icon=ft.Icons.FAVORITE,
        on_click=match_clicked,
        style=ft.ButtonStyle(
            color="#fff0f3",
            bgcolor="#ff88ac",
        ),
    )

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
    )

    async def load_saved_messages():
        historico = await carregar_historico()

        for item in historico:
            remetente = item.get("remetente")
            mensagem = item.get("mensagem")

            if remetente in ("usuario", "ia") and mensagem:
                if remetente == "usuario":
                    mensagens_usuario.append(mensagem)

                append_message(remetente, mensagem)

        if historico:
            messages_view.update()

    if hasattr(page, "run_task"):
        page.run_task(load_saved_messages)
    else:
        try:
            asyncio.get_running_loop().create_task(load_saved_messages())
        except RuntimeError:
            pass

  
    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Entrevista com IA", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                        ft.TextButton(
                            "Ver Perfil", 
                            icon=ft.Icons.ARROW_FORWARD, 
                            on_click=goto_profile_screen,
                            style=ft.ButtonStyle(color="#ff88ac")
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[match_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=6,
        ),
        padding=ft.padding.only(top=10, bottom=10, left=20, right=10)
    )

    sender_container = ft.Container(
        content=(ft.Row(controls=[field, send_buttom])),
        height= max(50, page.height*0.08),
        alignment= ft.Alignment.CENTER,
        padding=ft.padding.symmetric(horizontal=10)
    )

    column = ft.Column(
        expand=True,
        controls=[
            header,          
            messages_view,
            sender_container, 
        ],
    )

    return ft.View(
        route="/chat", 
        controls=[column],
        bgcolor=ft.Colors.PINK_50,
    )

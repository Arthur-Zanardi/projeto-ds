import flet as ft
from src.services.llm_conversation import llm_conversation
from src.services.api_client import enviar_mensagem_chat, carregar_historico

def chatView(page):
    async def goto_match_screen():
        page.views.pop()
        await page.push_route("/match")

    # --- Envio de mensagem ---
    def send_clicked(e):
        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(
                    controls=[ft.Text(f"{field.value}", size=24)], 
                    alignment=ft.CrossAxisAlignment.END,
                    wrap=True,
                    )), 
                bgcolor=ft.Colors.RED_100,
                padding=12,
                margin=12,
                width=200,
            )
        )
        
        field.value = " "

        messages_view.update()
        recieve_message()
    
    # --- Resposta da IA ---
    def recieve_message():

        response = llm_conversation(field.value)

        messages_view.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[ft.Text(
                        f"{response}", 
                        size=24)], 
                    alignment=ft.CrossAxisAlignment.END,
                    wrap=True,
                    ),
                bgcolor=ft.Colors.BLUE_100,
                padding=12,
                margin=12,
                width=350,
            )
        )

        messages_view.update()

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

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
    )

    # Apenas para depuração
    dev_button = ft.FilledIconButton(
        icon=ft.Icons.DEVELOPER_MODE_SHARP,
        on_click=goto_match_screen,
        style=ft.ButtonStyle(
            color= "#fff0f3",
            bgcolor= "#ff88ac",)
    )

    sender_container = ft.Container(
        content=(ft.Row(controls=[dev_button,field,send_buttom])),
        height= max(50, page.height*0.08),
        alignment= ft.Alignment.CENTER,
        #bgcolor="#000000",
    )

    column = ft.Column(
        expand=True,
        #tight=True,
        controls=[
            messages_view,
            sender_container, 
        ],
    )

    return ft.View(
        route="/login",
        controls=[column],
        bgcolor=ft.Colors.PINK_50,
    )
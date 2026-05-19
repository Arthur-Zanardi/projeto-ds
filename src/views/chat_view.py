import flet as ft
from src.services.llm_conversation import llm_conversation
from src.services.api_client import enviar_mensagem_chat, carregar_historico

def chatView(page):
    
    def goto_profile_screen(e):
        page.go("/profile")

    def send_clicked(e):
        texto_usuario = field.value.strip() 
        if not texto_usuario:
            return 

        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(
                    controls=[ft.Text(f"{texto_usuario}", size=24)], 
                    alignment=ft.CrossAxisAlignment.END,
                    wrap=True,
                    )), 
                bgcolor=ft.Colors.RED_100,
                padding=12,
                margin=12,
                width=200,
            )
        )
        
        field.value = "" 
        messages_view.update()
        
       
        recieve_message(texto_usuario) 
    
    def recieve_message(texto_enviado):
        response = llm_conversation(texto_enviado)

        messages_view.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[ft.Text(
                        f"{response}", 
                        size=24)], 
                    alignment=ft.CrossAxisAlignment.START, 
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

  
    header = ft.Container(
        content=ft.Row(
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
import flet as ft
from src.services.llm_conversation import llm_conversation

def chatView():
    def send_clicked(e):
        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(f"{field.value}", size=24)], alignment=ft.CrossAxisAlignment.END)), 
                bgcolor=ft.Colors.AMBER)
        )
        
        field.value = " "

        messages_view.update()
        recieve_message()
    
    def recieve_message():

        response = llm_conversation(field.value)

        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(f"{response}", size=24)], wrap=True)), 
                bgcolor=ft.Colors.BLUE_100,
                width=350,
                ),
        )

        messages_view.update()

    field = ft.TextField(
        hint_text="Digite aqui a sua mensagem",
    )

    send_buttom = ft.FilledIconButton(
        icon=ft.Icons.SEND,
        on_click=send_clicked,
    )

    messages_view = ft.ListView(
        expand=True,
        spacing=8,
        auto_scroll=True,
    )

    sender_container = ft.Container(
        content=(ft.Row(controls=[field,send_buttom])),
        height=100,
        width=350,
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
    )
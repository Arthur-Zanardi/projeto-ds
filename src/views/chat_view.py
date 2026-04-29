import flet as ft
from src.services.llm_service import gerar_resposta_ia

def main(page: ft.Page):
    def send_clicked(e):
        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(f"{field.value}", size=24)], alignment=ft.CrossAxisAlignment.END)), 
                bgcolor=ft.Colors.AMBER)
        )
        sent_messages.append(field.value)
        field.value = ""

        messages_view.update()

        response = gerar_resposta_ia(field.value)

        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(f"{response}", size=24)], wrap=True)), 
                bgcolor=ft.Colors.BLUE_100,
                width=350,
                ),
        )

        messages_view.update()

    sent_messages = []

    field = ft.TextField(
        hint_text="Digite aqui a sua mensagem",
    )

    send_buttom = ft.FilledIconButton(
        icon=ft.Icons.SEND,
        on_click=send_clicked,
    )

    messages_view = ft.Column(
        height=700,
        width=350,
        alignment=ft.MainAxisAlignment.END,
        controls=[],
    )

    sender_container = ft.Container(
        content=(ft.Row(controls=[field,send_buttom])),
        height=100,
        width=350,
        #padding=20,
    )

    column = ft.Column(
        width=500,
        height=1500,
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
        controls=[
            messages_view,
            sender_container, 
        ],
    )

    page.title = "MatchAI"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page.add(column)

if __name__ == "__main__":
    ft.run(main)
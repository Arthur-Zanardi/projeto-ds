import flet as ft
import requests

def main(page: ft.Page):
    def send_clicked(e):
        mensagem_usuario = (field.value or "").strip()
        if not mensagem_usuario:
            return

        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(mensagem_usuario, size=24)], alignment=ft.MainAxisAlignment.END)), 
                bgcolor=ft.Colors.AMBER)
        )
        sent_messages.append(mensagem_usuario)
        field.value = ""

        messages_view.update()

        try:

            resposta_api = requests.post(
                "http://127.0.0.1:8000/chat",
                timeout=15,
                json={"texto": mensagem_usuario}
            )

            if resposta_api.status_code == 200:
                response = resposta_api.json().get("resposta", "Desculpe, não consegui obter uma resposta da IA.")

            else:
                response = f"Erro na API: {resposta_api.status_code}"

        except Exception as ex:
            response = f"Erro de conexão com o servidor local: {ex}. A API está rodando?"

        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(f"{response}", size=24)], wrap=True)), 
                bgcolor=ft.Colors.BLUE_100,
                width=350,
                ),
        )

        messages_view.update()

    sent_messages = []

    # expand=True aqui faz o campo de texto se esticar horizontalmente
    field = ft.TextField(
        hint_text="Digite aqui a sua mensagem",
        expand=True 
    )

    send_buttom = ft.FilledIconButton(
        icon=ft.Icons.SEND,
        on_click=send_clicked,
    )

    # Trocamos Column por ListView para criar uma barra de rolagem!
    messages_view = ft.ListView(
        expand=True,      # Ocupa toda a altura vertical disponível
        spacing=10,       # Espaço entre uma mensagem e outra
        auto_scroll=True, # Rola a tela para baixo automaticamente em novas mensagens
    )

    # Container de envio (Campo de texto + Botão)
    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_buttom]),
        padding=10,
    )

    # Layout principal segurando a lista de mensagens e a barra de envio
    main_layout = ft.Column(
        expand=True, # Faz a interface preencher 100% da janela do app
        controls=[
            messages_view,
            sender_container, 
        ],
    )

    page.title = "MatchAI"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Adiciona o layout principal na página
    page.add(main_layout)

if __name__ == "__main__":
    ft.app(target=main)
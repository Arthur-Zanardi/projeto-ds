import flet as ft
import requests
import asyncio

def main(page: ft.Page):
    sent_messages = []

    status_text = ft.Text("", size=14)
    status_container = ft.Container(
        content=status_text,
        padding=10,
        bgcolor="#FFF3CD",
        visible=False,
    )

    match_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    match_container = ft.Container(
        content=match_text,
        padding=12,
        bgcolor="#E8F5E9",
        visible=False,
    )

    def set_status(message, visible=True):
        status_text.value = message
        status_container.visible = visible
        page.update()

    def show_snack(message):
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    # --- A MÁGICA DO POPUP ---
    texto_resultado = ft.Text("", size=18) 
    
    def fechar_dialogo():
        dlg_match.open = False
        page.update()

    dlg_match = ft.AlertDialog(
        title=ft.Text("💖 Deu Match!", size=22, weight=ft.FontWeight.BOLD),
        content=texto_resultado,
        actions=[ft.TextButton("Incrível!", on_click=lambda e: fechar_dialogo())]
    )

    page.dialog = dlg_match
    
    def acionar_match(e):
        print("--- INICIANDO BUSCA DE MATCH ---")
        
        if len(sent_messages) == 0:
            set_status("Converse com a IA primeiro para ela te conhecer!", visible=True)
            show_snack("Converse com a IA primeiro para ela te conhecer!")
            return

        botao_match = e.control
        botao_match.disabled = True
        match_container.visible = False
        page.update()

        set_status("Analisando sua personalidade... Isso pode levar ate 30 segundos!", visible=True)
        show_snack("Analisando sua personalidade... Isso pode levar ate 30 segundos!")

        async def executar_match():
            try:
                historico_completo = "\n".join(sent_messages)
                print("Enviando requisição para a API...")

                resposta = await asyncio.to_thread(
                    requests.post,
                    "http://127.0.0.1:8001/dar_match",
                    timeout=45,
                    json={"texto": historico_completo},
                )

                print(f"Status da API: {resposta.status_code}")
                dados = resposta.json()

                if dados.get("sucesso"):
                    match = dados["match"]
                    nome = match["nome"]
                    afinidade = match["afinidade"]

                    print(f"Sucesso! Match encontrado: {nome} ({afinidade})")

                    texto_resultado.value = f"Voce tem {afinidade} de compatibilidade com {nome}!"
                    match_text.value = texto_resultado.value
                    match_container.visible = True
                    status_container.visible = False
                    page.update()

                    try:
                        page.show_dialog(dlg_match)
                    except Exception:
                        pass
                else:
                    print(f"Falha na API: {dados.get('mensagem')}")
                    set_status(f"Erro: {dados.get('mensagem')}", visible=True)
                    show_snack(f"Erro: {dados.get('mensagem')}")

            except Exception as erro:
                print(f"Erro Crítico: {erro}")
                set_status(f"Erro na requisicao: {erro}. A API esta ligada?", visible=True)
                show_snack(f"Erro na requisicao: {erro}. A API esta ligada?")

            finally:
                botao_match.disabled = False
                page.update()
                print("--- PROCESSO FINALIZADO ---")

        page.run_task(executar_match)

    def send_clicked(e):
        mensagem_usuario = (field.value or "").strip()
        if not mensagem_usuario:
            return

        messages_view.controls.append(
            ft.Container(
                content=(ft.Row(controls=[ft.Text(mensagem_usuario, size=24)], alignment=ft.MainAxisAlignment.END)), 
                bgcolor="amber") 
        )
        
        sent_messages.append(mensagem_usuario)
        field.value = ""

        messages_view.update()

        try:
            resposta_api = requests.post(
                "http://127.0.0.1:8001/chat",
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
                bgcolor="lightblue", 
                width=350,
                ),
        )

        messages_view.update()

    field = ft.TextField(
        hint_text="Digite aqui a sua mensagem",
        expand=True 
    )

    send_buttom = ft.FilledIconButton(
        icon=ft.Icons.SEND,
        on_click=send_clicked,
    )

    messages_view = ft.ListView(
        expand=True,      
        spacing=10,       
        auto_scroll=True, 
    )
    
    # --- NOVO: Função que puxa o histórico ao abrir ---
    def carregar_historico_inicial():
        try:
            resposta = requests.get("http://127.0.0.1:8001/historico", timeout=5)
            if resposta.status_code == 200:
                mensagens = resposta.json().get("historico", [])
                for msg in mensagens:
                    if msg["remetente"] == "usuario":
                        messages_view.controls.append(
                            ft.Container(
                                content=(ft.Row(controls=[ft.Text(msg["mensagem"], size=24)], alignment=ft.MainAxisAlignment.END)), 
                                bgcolor="amber"
                            )
                        )
                        # Salva na memória para o Match usar depois!
                        sent_messages.append(msg["mensagem"])
                    else:
                        messages_view.controls.append(
                            ft.Container(
                                content=(ft.Row(controls=[ft.Text(msg["mensagem"], size=24)], wrap=True)), 
                                bgcolor="lightblue", 
                                width=350,
                            )
                        )
        except Exception as e:
            print(f"Aviso: Não foi possível carregar histórico. API desligada? Erro: {e}")

    # Executa a função antes de desenhar a tela
    carregar_historico_inicial()

    sender_container = ft.Container(
        content=ft.Row(controls=[field, send_buttom]),
        padding=10,
    )

    main_layout = ft.Column(
        expand=True, 
        controls=[
            status_container,
            match_container,
            messages_view,
            sender_container, 
        ],
    )

    page.title = "MatchAI"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    page.appbar = ft.AppBar(
        title=ft.Text("MatchAI"),
        center_title=True,
        bgcolor="#EEEEEE", 
        actions=[
            ft.ElevatedButton(
                "Encontrar meu Match! 💖", 
                on_click=acionar_match,
                style=ft.ButtonStyle(color="pink", bgcolor="white") 
            ),
            ft.Container(width=10) 
        ]
    )
    
    page.add(main_layout)

if __name__ == "__main__":
    ft.app(target=main)
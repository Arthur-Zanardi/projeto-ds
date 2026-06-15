import flet as ft
from src.services.sqlite_db import SQLiteUserRepository
from src.controllers.login_controller import LoginController
from src.views.login_view import loginView

from src.views.chat_view import chatView

# Tiramos o async do main, voltando ao padrão hiper estável
def main(page: ft.Page):
    page.title = "MatchAi"
    
    page.window.width = 450
    page.window.height = 800

    usuario_repo = SQLiteUserRepository()
    autenticacao_controller = LoginController(usuario_repo)

    # Função gerenciadora de rotas padrão
    def route_change(e):
        page.views.clear()
        
        if page.route == "/login" or page.route == "/":
            page.views.append(
                loginView(page, autenticacao_controller)
            )
            
        elif page.route == "/chat":
            
            # === NOVA FORMA DE VERIFICAR A SESSÃO ===
            if hasattr(page, "usuario_logado") and page.usuario_logado:
                
                page.views.append(
                    chatView(page) 
                )
            else:
                page.route = "/login"
                page.views.append(loginView(page, autenticacao_controller))
                
        page.update()

    page.on_route_change = route_change
    
    # === O PULO DO GATO ===
    # Em vez de mandar o Flet processar uma mudança de rota assim que abre 
    # (o que causa a tela preta), nós definimos a rota raiz de forma "física" e 
    # engatilhamos a renderização inicial instantaneamente.
    page.route = "/"
    route_change(None)

if __name__ == "__main__":
    ft.run(main)
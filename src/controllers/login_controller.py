# src/controllers/login_controller.py
import bcrypt
from src.services.interfaces import IUserRepository

class LoginController:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    def realizar_login(self, email: str, senha_pura: str) -> dict | None:
        """Retorna o usuário se as credenciais forem válidas, ou None se falhar."""
        if not email or not senha_pura:
            return None

        usuario = self.user_repo.buscar_usuario_por_email(email)
        if usuario:
            # Verifica se o hash da senha bate com a senha digitada
            if bcrypt.checkpw(senha_pura.encode('utf-8'), usuario["senha_hash"].encode('utf-8')):
                return usuario
        return None

    def realizar_cadastro(
        self,
        email: str,
        senha_pura: str,
        nome: str | None = None,
        idade=None,
        foto_url=None,
        descricao=None,
        localizacao=None,
        cargo=None,
    ) -> bool:
        """Retorna True se o cadastro for bem-sucedido, ou False se houver erro."""
        if not email or not senha_pura:
            return False
        return self.user_repo.criar_usuario(
            email=email,
            senha_pura=senha_pura,
            nome=nome,
            idade=idade,
            foto_url=foto_url,
            descricao=descricao,
            localizacao=localizacao,
            cargo=cargo,
        )

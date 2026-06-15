# src/services/interfaces.py
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    def criar_usuario(self, nome: str, email: str, senha_pura: str) -> bool:
        pass

    @abstractmethod
    def buscar_usuario_por_email(self, email: str) -> dict:
        pass

class IMatchRepository(ABC):
    @abstractmethod
    def salvar_perfil_usuario(self, id_usuario: str, nome: str, dados_extraidos_ia: dict) -> list:
        pass

    @abstractmethod
    def buscar_melhor_match(self, id_usuario_buscando: str, vetor_do_usuario: list, quantidade: int = 1) -> list:
        pass
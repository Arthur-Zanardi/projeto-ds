"""Configuração centralizada do MatchAI.

Lê variáveis do ambiente (e de um arquivo `.env`) com `pydantic-settings`.
Importar este módulo é barato e sem efeitos colaterais: a validação de
variáveis obrigatórias em produção é feita explicitamente por
`settings.validar_obrigatorias()`, chamada no startup da API (lifespan),
para não exigir segredos de banco/JWT no processo do frontend.
"""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ambiente
    env: str = "dev"

    # Banco de dados (PostgreSQL + pgvector)
    database_url: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalizar_driver(cls, valor: str) -> str:
        # Render/Heroku entregam "postgres://"; SQLAlchemy precisa do driver psycopg v3.
        if valor.startswith("postgres://"):
            return "postgresql+psycopg://" + valor[len("postgres://"):]
        if valor.startswith("postgresql://"):
            return "postgresql+psycopg://" + valor[len("postgresql://"):]
        return valor

    # Autenticação JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Integração LLM
    groq_api_key: str = ""

    # Frontend / API
    matchai_api_base_url: str = "http://127.0.0.1:8000"

    # CORS (lista separada por vírgula, ou "*")
    cors_allow_origins: str = ""

    # Administradores (e-mails separados por vírgula)
    admin_emails: str = ""

    # Seed automático apenas em dev
    seed_on_startup: bool = True

    @property
    def is_prod(self) -> bool:
        return self.env.strip().lower() in {"prod", "production"}

    @property
    def cors_origins_list(self) -> list[str]:
        bruto = (self.cors_allow_origins or "").strip()
        if bruto == "*":
            return ["*"]
        return [origem.strip() for origem in bruto.split(",") if origem.strip()]

    @property
    def admin_emails_set(self) -> set[str]:
        return {e.strip().lower() for e in (self.admin_emails or "").split(",") if e.strip()}

    def validar_obrigatorias(self) -> "Settings":
        """Falha rápido se faltarem variáveis obrigatórias em produção."""
        if self.is_prod:
            obrigatorias = {
                "DATABASE_URL": self.database_url,
                "JWT_SECRET": self.jwt_secret,
                "GROQ_API_KEY": self.groq_api_key,
            }
            faltando = [nome for nome, valor in obrigatorias.items() if not str(valor).strip()]
            if faltando:
                raise RuntimeError(
                    "Variáveis de ambiente obrigatórias ausentes em prod: "
                    + ", ".join(faltando)
                )
            if len(self.jwt_secret) < 16:
                raise RuntimeError("JWT_SECRET muito curto para produção (use >= 32 caracteres).")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

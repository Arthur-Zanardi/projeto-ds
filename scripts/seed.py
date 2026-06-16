"""Popula o banco com perfis mock (Maria, Carmen, Lia).

Substitui o antigo `popular_banco_mock`. Idempotente (upsert). Rode com:
    python -m scripts.seed
Em produção, rode manualmente; em dev o entrypoint pode rodar automaticamente.
"""
import logging

from src.services.database import criar_vetor_mock_padrao, salvar_perfil_vetorial
from src.services.postgres_db import salvar_perfil_publico

logger = logging.getLogger(__name__)

PERFIS_MOCK = [
    {
        "id": "user_maria",
        "nome": "Maria",
        "idade": 22,
        "localizacao": "Recife, PE",
        "cargo": "Estudante de Tecnologia",
        "descricao": "Curiosa por tecnologia, cafeterias escondidas e conversas que pulam de animes para planos de viagem.",
        "foto_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=900&h=1200&fit=crop",
        "vetores": {
            "psicologico": {
                "extroversao": 0.6, "abertura_experiencias": 0.6, "romantismo_afeto": 0.5,
                "ritmo_vida": 0.6, "logica_vs_emocao": 0.7, "resolucao_conflitos": 0.5,
                "competitividade_cooperacao": 0.5,
            },
            "valores": {
                "ambicao_carreira": 0.6, "conservadorismo": 0.4, "espectro_politico": 0.5,
                "gestao_financeira": 0.6, "religiosidade": 0.4, "gosto_festas": 0.6,
            },
            "interesses": {
                "animes": 0.9, "filmes": 0.6, "series": 0.7, "livros_ficcao": 0.8,
                "videogames": 0.7, "jogos_tabuleiro": 0.4, "tecnologia": 0.6, "academia": 0.8,
                "esportes": 0.8, "futebol": 0.9, "dancas": 0.3, "musica": 0.6,
                "tocar_instrumentos": 0.2, "fotografia": 0.4, "culinaria": 0.6, "idiomas": 0.6,
                "celebridades": 0.2, "historia": 0.5, "geografia": 0.4, "geopolitica": 0.5,
                "astronomia": 0.5,
            },
        },
    },
    {
        "id": "user_carmen",
        "nome": "Carmen",
        "idade": 24,
        "localizacao": "Olinda, PE",
        "cargo": "Designer",
        "descricao": "Designer tranquila, apaixonada por musica, cozinhar no fim de semana e encontrar beleza nas pequenas rotinas.",
        "foto_url": "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=900&h=1200&fit=crop",
        "vetores": {
            "psicologico": {
                "extroversao": 0.2, "abertura_experiencias": 0.2, "romantismo_afeto": 0.8,
                "ritmo_vida": 0.2, "logica_vs_emocao": 0.2, "resolucao_conflitos": 0.2,
                "competitividade_cooperacao": 0.2,
            },
            "valores": {
                "ambicao_carreira": 0.2, "conservadorismo": 1.0, "espectro_politico": 0.9,
                "gestao_financeira": 0.2, "religiosidade": 1.0, "gosto_festas": 0.0,
            },
            "interesses": {
                "animes": 0.0, "filmes": 0.2, "series": 0.2, "livros_ficcao": 0.1,
                "videogames": 0.0, "jogos_tabuleiro": 0.1, "tecnologia": 0.1, "academia": 0.0,
                "esportes": 0.0, "futebol": 0.0, "dancas": 0.1, "musica": 0.5,
                "tocar_instrumentos": 0.0, "fotografia": 0.1, "culinaria": 0.8, "idiomas": 0.1,
                "celebridades": 0.8, "historia": 0.2, "geografia": 0.2, "geopolitica": 0.1,
                "astronomia": 0.0,
            },
        },
    },
    {
        "id": "user_lia",
        "nome": "Lia",
        "idade": 21,
        "localizacao": "Joao Pessoa, PB",
        "cargo": "Fotografa",
        "descricao": "Fotografa de rua, fa de trilhas curtas, playlists enormes e gente que sabe rir de um dia estranho.",
        "foto_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=900&h=1200&fit=crop",
        "vetores": None,
    },
]


def popular_perfis_mock() -> int:
    total = 0
    for perfil in PERFIS_MOCK:
        vetores = perfil["vetores"] or criar_vetor_mock_padrao(perfil["id"])
        salvar_perfil_vetorial(perfil["id"], perfil["nome"], vetores)
        salvar_perfil_publico(
            usuario=perfil["id"],
            nome=perfil["nome"],
            idade=perfil["idade"],
            foto_url=perfil["foto_url"],
            descricao=perfil["descricao"],
            localizacao=perfil["localizacao"],
            cargo=perfil["cargo"],
            origem="mock",
            mock_customizado=False,
        )
        total += 1
    logger.info("Seed concluido: %d perfis mock.", total)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    popular_perfis_mock()

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from src.schema.schema_vetores import flatten_profile_vectors, normalize_profile_vectors


COLLECTION_NAME = "perfis_matchai"
CHROMA_PATH = "./banco_vetorial"


@lru_cache(maxsize=1)
def _collection():
    try:
        import chromadb
    except ImportError as exc:
        print(f"ChromaDB indisponivel: {exc}")
        return None

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def salvar_perfil_usuario(
    id_usuario: str,
    nome: str,
    dados_extraidos_ia: dict[str, Any],
    bio: str = "",
) -> list[float]:
    profile_json = normalize_profile_vectors(dados_extraidos_ia)
    vetor_usuario = flatten_profile_vectors(profile_json)
    collection = _collection()
    if collection is None:
        return vetor_usuario

    metadata = {
        "nome": nome,
        "bio": bio or "",
        "profile_json": json.dumps(profile_json, ensure_ascii=False),
    }
    collection.upsert(
        ids=[id_usuario],
        embeddings=[vetor_usuario],
        metadatas=[metadata],
        documents=[f"Perfil de {nome}"],
    )
    print(f"Perfil vetorial de {nome} salvo: {len(vetor_usuario)} dimensoes.")
    return vetor_usuario


def buscar_melhor_match(
    id_usuario_buscando: str,
    vetor_do_usuario: list[float],
    quantidade: int = 1,
) -> list[dict[str, Any]]:
    collection = _collection()
    if collection is None:
        return []

    total_para_buscar = max(quantidade + 10, 12)
    resultados = collection.query(
        query_embeddings=[vetor_do_usuario],
        n_results=total_para_buscar,
        include=["metadatas", "documents", "distances"],
    )

    matches_reais: list[dict[str, Any]] = []
    ids = resultados.get("ids", [[]])[0]
    distances = resultados.get("distances", [[]])[0]
    metadatas = resultados.get("metadatas", [[]])[0]

    for index, id_encontrado in enumerate(ids):
        if id_encontrado == id_usuario_buscando:
            continue

        distancia = float(distances[index])
        afinidade_porcentagem = round(max(0.0, (1 - distancia) * 100), 1)
        metadados = metadatas[index] or {}
        profile_json = _profile_from_metadata(metadados)

        matches_reais.append(
            {
                "id": id_encontrado,
                "nome": metadados.get("nome", "Desconhecido"),
                "bio": metadados.get("bio", ""),
                "afinidade": f"{afinidade_porcentagem}%",
                "afinidade_numero": afinidade_porcentagem,
                "distancia_matematica": distancia,
                "profile_json": profile_json,
            }
        )

        if len(matches_reais) == quantidade:
            break

    return matches_reais


def obter_perfil_vetorial(id_usuario: str) -> dict[str, Any] | None:
    collection = _collection()
    if collection is None:
        return None

    resultado = collection.get(ids=[id_usuario], include=["metadatas"])
    if not resultado.get("ids"):
        return None

    metadata = (resultado.get("metadatas") or [{}])[0] or {}
    return {
        "id": id_usuario,
        "nome": metadata.get("nome", "Desconhecido"),
        "bio": metadata.get("bio", ""),
        "profile_json": _profile_from_metadata(metadata),
    }


def popular_banco_mock() -> None:
    collection = _collection()
    if collection is None:
        return

    perfis = [
        (
            "user_maria",
            "Maria",
            "Designer, leitora de fantasia e parceira para jogos, academia e futebol.",
            {
                "psicologico": {
                    "extroversao": 0.6,
                    "abertura_experiencias": 0.7,
                    "romantismo_afeto": 0.7,
                    "ritmo_vida": 0.6,
                    "logica_vs_emocao": 0.6,
                    "resolucao_conflitos": 0.5,
                    "competitividade_cooperacao": 0.4,
                },
                "valores": {
                    "ambicao_carreira": 0.7,
                    "conservadorismo": 0.3,
                    "espectro_politico": 0.35,
                    "gestao_financeira": 0.6,
                    "religiosidade": 0.2,
                    "gosto_festas": 0.5,
                },
                "interesses": {
                    "animes": 0.9,
                    "filmes": 0.7,
                    "series": 0.8,
                    "livros_ficcao": 0.9,
                    "videogames": 0.7,
                    "jogos_tabuleiro": 0.6,
                    "tecnologia": 0.6,
                    "academia": 0.8,
                    "esportes": 0.8,
                    "futebol": 0.9,
                    "dancas": 0.4,
                    "musica": 0.7,
                    "tocar_instrumentos": 0.3,
                    "fotografia": 0.5,
                    "culinaria": 0.6,
                    "idiomas": 0.6,
                    "celebridades": 0.2,
                    "historia": 0.5,
                    "geografia": 0.4,
                    "geopolitica": 0.5,
                    "astronomia": 0.5,
                },
            },
        ),
        (
            "user_luiza",
            "Luiza",
            "Musica, astronomia, conversas profundas e rotina mais tranquila.",
            {
                "psicologico": {
                    "extroversao": 0.35,
                    "abertura_experiencias": 0.85,
                    "romantismo_afeto": 0.8,
                    "ritmo_vida": 0.35,
                    "logica_vs_emocao": 0.35,
                    "resolucao_conflitos": 0.45,
                    "competitividade_cooperacao": 0.25,
                },
                "valores": {
                    "ambicao_carreira": 0.55,
                    "conservadorismo": 0.15,
                    "espectro_politico": 0.2,
                    "gestao_financeira": 0.6,
                    "religiosidade": 0.1,
                    "gosto_festas": 0.15,
                },
                "interesses": {
                    "animes": 0.7,
                    "filmes": 0.6,
                    "series": 0.7,
                    "livros_ficcao": 0.8,
                    "videogames": 0.4,
                    "jogos_tabuleiro": 0.5,
                    "tecnologia": 0.7,
                    "academia": 0.4,
                    "esportes": 0.2,
                    "futebol": 0.1,
                    "dancas": 0.4,
                    "musica": 0.95,
                    "tocar_instrumentos": 0.9,
                    "fotografia": 0.6,
                    "culinaria": 0.6,
                    "idiomas": 0.7,
                    "celebridades": 0.2,
                    "historia": 0.6,
                    "geografia": 0.6,
                    "geopolitica": 0.7,
                    "astronomia": 0.95,
                },
            },
        ),
        (
            "user_carmen",
            "Carmen",
            "Caseira, religiosa, conservadora e apaixonada por culinaria.",
            {
                "psicologico": {
                    "extroversao": 0.25,
                    "abertura_experiencias": 0.2,
                    "romantismo_afeto": 0.8,
                    "ritmo_vida": 0.25,
                    "logica_vs_emocao": 0.25,
                    "resolucao_conflitos": 0.3,
                    "competitividade_cooperacao": 0.2,
                },
                "valores": {
                    "ambicao_carreira": 0.35,
                    "conservadorismo": 0.95,
                    "espectro_politico": 0.85,
                    "gestao_financeira": 0.55,
                    "religiosidade": 0.95,
                    "gosto_festas": 0.05,
                },
                "interesses": {
                    "animes": 0.0,
                    "filmes": 0.3,
                    "series": 0.3,
                    "livros_ficcao": 0.2,
                    "videogames": 0.0,
                    "jogos_tabuleiro": 0.1,
                    "tecnologia": 0.1,
                    "academia": 0.2,
                    "esportes": 0.1,
                    "futebol": 0.0,
                    "dancas": 0.1,
                    "musica": 0.55,
                    "tocar_instrumentos": 0.0,
                    "fotografia": 0.2,
                    "culinaria": 0.9,
                    "idiomas": 0.2,
                    "celebridades": 0.7,
                    "historia": 0.3,
                    "geografia": 0.3,
                    "geopolitica": 0.15,
                    "astronomia": 0.1,
                },
            },
        ),
    ]

    for user_id, nome, bio, profile_json in perfis:
        salvar_perfil_usuario(user_id, nome, profile_json, bio=bio)


def _profile_from_metadata(metadata: dict[str, Any]) -> dict[str, dict[str, float]]:
    raw = metadata.get("profile_json")
    if isinstance(raw, str):
        try:
            return normalize_profile_vectors(json.loads(raw))
        except json.JSONDecodeError:
            pass
    if isinstance(raw, dict):
        return normalize_profile_vectors(raw)
    return normalize_profile_vectors({})

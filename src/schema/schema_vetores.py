from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field


BASE_VECTOR_SCHEMA: dict[str, dict[str, float]] = {
    "psicologico": {
        "extroversao": 0.5,
        "abertura_experiencias": 0.5,
        "romantismo_afeto": 0.5,
        "ritmo_vida": 0.5,
        "logica_vs_emocao": 0.5,
        "resolucao_conflitos": 0.5,
        "competitividade_cooperacao": 0.5,
    },
    "valores": {
        "ambicao_carreira": 0.5,
        "conservadorismo": 0.5,
        "espectro_politico": 0.5,
        "gestao_financeira": 0.5,
        "religiosidade": 0.5,
        "gosto_festas": 0.5,
    },
    "interesses": {
        "animes": 0.5,
        "filmes": 0.5,
        "series": 0.5,
        "livros_ficcao": 0.5,
        "videogames": 0.5,
        "jogos_tabuleiro": 0.5,
        "tecnologia": 0.5,
        "academia": 0.5,
        "esportes": 0.5,
        "futebol": 0.5,
        "dancas": 0.5,
        "musica": 0.5,
        "tocar_instrumentos": 0.5,
        "fotografia": 0.5,
        "culinaria": 0.5,
        "idiomas": 0.5,
        "celebridades": 0.5,
        "historia": 0.5,
        "geografia": 0.5,
        "geopolitica": 0.5,
        "astronomia": 0.5,
    },
}

PHYSICAL_VECTOR_SCHEMA: dict[str, float] = {
    "olhos_azuis": 0.5,
    "olhos_castanhos": 0.5,
    "olhos_verdes_mel": 0.5,
    "cabelo_escuro": 0.5,
    "cabelo_claro_ruivo": 0.5,
    "cabelo_cacheado_crespo": 0.5,
    "oculos": 0.5,
    "tatuagens_piercings": 0.5,
    "estilo_esportivo": 0.5,
    "estilo_elegante": 0.5,
    "estilo_alternativo": 0.5,
    "altura_baixa": 0.5,
    "altura_media": 0.5,
    "altura_alta": 0.5,
    "corpo_magro": 0.5,
    "corpo_medio": 0.5,
    "corpo_forte": 0.5,
}

VECTOR_SCHEMA: dict[str, dict[str, float]] = {
    **BASE_VECTOR_SCHEMA,
    "fisico": deepcopy(PHYSICAL_VECTOR_SCHEMA),
    "atracao": deepcopy(PHYSICAL_VECTOR_SCHEMA),
}

BASE_VECTOR_GROUPS = ("psicologico", "valores", "interesses")
PHYSICAL_VECTOR_GROUPS = ("fisico", "atracao")

VECTOR_ORDER: list[tuple[str, str]] = [
    (grupo, chave)
    for grupo, campos in VECTOR_SCHEMA.items()
    for chave in campos.keys()
]

STORAGE_VECTOR_ORDER: list[tuple[str, str]] = [
    (grupo, chave)
    for grupo in (*BASE_VECTOR_GROUPS, "fisico", "atracao")
    for chave in VECTOR_SCHEMA[grupo].keys()
]

QUERY_VECTOR_ORDER: list[tuple[str, str]] = [
    (grupo, chave)
    for grupo in (*BASE_VECTOR_GROUPS, "atracao", "fisico")
    for chave in VECTOR_SCHEMA[grupo].keys()
]

INTEREST_LABELS: dict[str, str] = {
    "animes": "Animes",
    "filmes": "Filmes",
    "series": "Series",
    "livros_ficcao": "Livros de ficcao",
    "videogames": "Videogames",
    "jogos_tabuleiro": "Jogos de tabuleiro",
    "tecnologia": "Tecnologia",
    "academia": "Academia",
    "esportes": "Esportes",
    "futebol": "Futebol",
    "dancas": "Dancas",
    "musica": "Musica",
    "tocar_instrumentos": "Instrumentos",
    "fotografia": "Fotografia",
    "culinaria": "Culinaria",
    "idiomas": "Idiomas",
    "celebridades": "Cultura pop",
    "historia": "Historia",
    "geografia": "Geografia",
    "geopolitica": "Geopolitica",
    "astronomia": "Astronomia",
}

VALUE_LABELS: dict[str, str] = {
    "ambicao_carreira": "Ambicao e carreira",
    "conservadorismo": "Conservadorismo",
    "espectro_politico": "Espectro politico",
    "gestao_financeira": "Gestao financeira",
    "religiosidade": "Religiosidade",
    "gosto_festas": "Gosto por festas",
}

PHYSICAL_LABELS: dict[str, str] = {
    "olhos_azuis": "Olhos azuis",
    "olhos_castanhos": "Olhos castanhos",
    "olhos_verdes_mel": "Olhos verdes/mel",
    "cabelo_escuro": "Cabelo escuro",
    "cabelo_claro_ruivo": "Cabelo claro/ruivo",
    "cabelo_cacheado_crespo": "Cabelo cacheado/crespo",
    "oculos": "Oculos",
    "tatuagens_piercings": "Tatuagens/piercings",
    "estilo_esportivo": "Estilo esportivo",
    "estilo_elegante": "Estilo elegante",
    "estilo_alternativo": "Estilo alternativo",
    "altura_baixa": "Altura baixa",
    "altura_media": "Altura media",
    "altura_alta": "Altura alta",
    "corpo_magro": "Corpo magro",
    "corpo_medio": "Corpo medio",
    "corpo_forte": "Corpo forte",
}

GROUP_LABELS: dict[str, str] = {
    "psicologico": "Perfil psicologico",
    "valores": "Valores",
    "interesses": "Interesses",
    "fisico": "Caracteristicas fisicas",
    "atracao": "Atracao fisica",
}

DEFAULT_VISIBLE_FIELDS: dict[str, bool] = {
    "bio": True,
    "interesses": True,
    "valores": False,
    "psicologico": False,
    "fisico": False,
}


def clamp_score(value: Any, default: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def default_profile_vectors() -> dict[str, dict[str, float]]:
    return deepcopy(VECTOR_SCHEMA)


def normalize_profile_vectors(data: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    normalized = default_profile_vectors()
    if not isinstance(data, dict):
        return normalized

    for grupo, campos in VECTOR_SCHEMA.items():
        incoming_group = data.get(grupo, {})
        if not isinstance(incoming_group, dict):
            continue

        for chave, default in campos.items():
            normalized[grupo][chave] = clamp_score(incoming_group.get(chave), default)

    return normalized


def flatten_profile_vectors(data: dict[str, Any] | None) -> list[float]:
    return flatten_storage_vectors(data)


def flatten_storage_vectors(data: dict[str, Any] | None) -> list[float]:
    normalized = normalize_profile_vectors(data)
    return [normalized[grupo][chave] for grupo, chave in STORAGE_VECTOR_ORDER]


def flatten_query_vectors(data: dict[str, Any] | None) -> list[float]:
    normalized = normalize_profile_vectors(data)
    return [normalized[grupo][chave] for grupo, chave in QUERY_VECTOR_ORDER]


def flatten_base_vectors(data: dict[str, Any] | None) -> list[float]:
    normalized = normalize_profile_vectors(data)
    return [
        normalized[grupo][chave]
        for grupo in BASE_VECTOR_GROUPS
        for chave in VECTOR_SCHEMA[grupo].keys()
    ]


def vector_to_profile(vector: list[float]) -> dict[str, dict[str, float]]:
    profile = default_profile_vectors()
    for index, (grupo, chave) in enumerate(STORAGE_VECTOR_ORDER):
        if index >= len(vector):
            break
        profile[grupo][chave] = clamp_score(vector[index])
    return profile


def merge_interests_override(
    profile: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> dict[str, dict[str, float]]:
    normalized = normalize_profile_vectors(profile)
    if not isinstance(overrides, dict):
        return normalized

    for chave in VECTOR_SCHEMA["interesses"].keys():
        if chave in overrides:
            normalized["interesses"][chave] = clamp_score(overrides[chave])

    return normalized


def merge_physical_profile(
    profile: dict[str, Any] | None,
    physical: dict[str, Any] | None,
) -> dict[str, dict[str, float]]:
    normalized = normalize_profile_vectors(profile)
    if not isinstance(physical, dict):
        return normalized

    for chave in PHYSICAL_VECTOR_SCHEMA.keys():
        if chave in physical:
            normalized["fisico"][chave] = clamp_score(physical[chave])

    return normalized


def merge_attraction_profile(
    profile: dict[str, Any] | None,
    attraction: dict[str, Any] | None,
) -> dict[str, dict[str, float]]:
    normalized = normalize_profile_vectors(profile)
    if not isinstance(attraction, dict):
        return normalized

    for chave in PHYSICAL_VECTOR_SCHEMA.keys():
        if chave in attraction:
            normalized["atracao"][chave] = clamp_score(attraction[chave])

    return normalized


def merge_extracted_profile(
    current_profile: dict[str, Any] | None,
    extracted_profile: dict[str, Any] | None,
) -> dict[str, dict[str, float]]:
    current = normalize_profile_vectors(current_profile)
    extracted = normalize_profile_vectors(extracted_profile)

    for grupo in ("psicologico", "valores", "interesses", "atracao"):
        current[grupo] = extracted[grupo]
    return current


def get_dimension(profile: dict[str, Any] | None, path: str) -> float:
    normalized = normalize_profile_vectors(profile)
    if "." in path:
        grupo, chave = path.split(".", 1)
    else:
        grupo, chave = "valores", path

    if grupo not in normalized or chave not in normalized[grupo]:
        return 0.5
    return normalized[grupo][chave]


def public_profile_from_visibility(
    profile_json: dict[str, Any] | None,
    visible_fields: dict[str, bool] | None,
) -> dict[str, Any]:
    normalized = normalize_profile_vectors(profile_json)
    visibility = {**DEFAULT_VISIBLE_FIELDS, **(visible_fields or {})}
    public: dict[str, Any] = {}

    if visibility.get("psicologico"):
        public["psicologico"] = normalized["psicologico"]
    if visibility.get("valores"):
        public["valores"] = normalized["valores"]
    if visibility.get("interesses"):
        public["interesses"] = normalized["interesses"]
    if visibility.get("fisico"):
        public["fisico"] = normalized["fisico"]

    return public


def top_interests_summary(profile_json: dict[str, Any] | None, limit: int = 4) -> list[dict[str, Any]]:
    normalized = normalize_profile_vectors(profile_json)
    ranked = sorted(
        normalized["interesses"].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"key": key, "label": INTEREST_LABELS.get(key, key), "score": score}
        for key, score in ranked
        if score > 0.55
    ][:limit]


def top_physical_matches(
    user_profile: dict[str, Any] | None,
    candidate_profile: dict[str, Any] | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    user = normalize_profile_vectors(user_profile)
    candidate = normalize_profile_vectors(candidate_profile)
    scores: list[tuple[str, float]] = []
    for key in PHYSICAL_VECTOR_SCHEMA.keys():
        score = min(user["atracao"][key], candidate["fisico"][key])
        if score >= 0.7:
            score -= abs(user["atracao"][key] - candidate["fisico"][key])
            scores.append((key, score))

    return [
        {"key": key, "label": PHYSICAL_LABELS.get(key, key), "score": score}
        for key, score in sorted(scores, key=lambda item: item[1], reverse=True)[:limit]
    ]


class VetorPsicologico(BaseModel):
    extroversao: float = Field(default=0.5)
    abertura_experiencias: float = Field(default=0.5)
    romantismo_afeto: float = Field(default=0.5)
    ritmo_vida: float = Field(default=0.5)
    logica_vs_emocao: float = Field(default=0.5)
    resolucao_conflitos: float = Field(default=0.5)
    competitividade_cooperacao: float = Field(default=0.5)


class VetorValores(BaseModel):
    ambicao_carreira: float = Field(default=0.5)
    conservadorismo: float = Field(default=0.5)
    espectro_politico: float = Field(default=0.5)
    gestao_financeira: float = Field(default=0.5)
    religiosidade: float = Field(default=0.5)
    gosto_festas: float = Field(default=0.5)


class VetorInteresses(BaseModel):
    animes: float = Field(default=0.5)
    filmes: float = Field(default=0.5)
    series: float = Field(default=0.5)
    livros_ficcao: float = Field(default=0.5)
    videogames: float = Field(default=0.5)
    jogos_tabuleiro: float = Field(default=0.5)
    tecnologia: float = Field(default=0.5)
    academia: float = Field(default=0.5)
    esportes: float = Field(default=0.5)
    futebol: float = Field(default=0.5)
    dancas: float = Field(default=0.5)
    musica: float = Field(default=0.5)
    tocar_instrumentos: float = Field(default=0.5)
    fotografia: float = Field(default=0.5)
    culinaria: float = Field(default=0.5)
    idiomas: float = Field(default=0.5)
    celebridades: float = Field(default=0.5)
    historia: float = Field(default=0.5)
    geografia: float = Field(default=0.5)
    geopolitica: float = Field(default=0.5)
    astronomia: float = Field(default=0.5)


class VetorFisico(BaseModel):
    olhos_azuis: float = Field(default=0.5)
    olhos_castanhos: float = Field(default=0.5)
    olhos_verdes_mel: float = Field(default=0.5)
    cabelo_escuro: float = Field(default=0.5)
    cabelo_claro_ruivo: float = Field(default=0.5)
    cabelo_cacheado_crespo: float = Field(default=0.5)
    oculos: float = Field(default=0.5)
    tatuagens_piercings: float = Field(default=0.5)
    estilo_esportivo: float = Field(default=0.5)
    estilo_elegante: float = Field(default=0.5)
    estilo_alternativo: float = Field(default=0.5)
    altura_baixa: float = Field(default=0.5)
    altura_media: float = Field(default=0.5)
    altura_alta: float = Field(default=0.5)
    corpo_magro: float = Field(default=0.5)
    corpo_medio: float = Field(default=0.5)
    corpo_forte: float = Field(default=0.5)


class PerfilUsuarioVetorizado(BaseModel):
    psicologico: VetorPsicologico = Field(default_factory=VetorPsicologico)
    valores: VetorValores = Field(default_factory=VetorValores)
    interesses: VetorInteresses = Field(default_factory=VetorInteresses)
    fisico: VetorFisico = Field(default_factory=VetorFisico)
    atracao: VetorFisico = Field(default_factory=VetorFisico)

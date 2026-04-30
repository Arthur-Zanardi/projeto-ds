from __future__ import annotations

from typing import Any

from src.schema.schema_vetores import (
    INTEREST_LABELS,
    VALUE_LABELS,
    get_dimension,
    normalize_profile_vectors,
    public_profile_from_visibility,
)


def passes_value_filters(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
    filters: list[dict[str, Any]],
) -> tuple[bool, str | None]:
    for item in filters:
        if not item.get("active", True):
            continue

        key = item.get("key", "")
        if not key:
            continue

        user_value = get_dimension(user_profile, key)
        candidate_value = get_dimension(candidate_profile, key)

        min_value = item.get("min_value")
        max_value = item.get("max_value")
        max_delta = item.get("max_delta")

        if min_value is not None and candidate_value < float(min_value):
            return False, f"{key} abaixo do filtro definido."
        if max_value is not None and candidate_value > float(max_value):
            return False, f"{key} acima do filtro definido."
        if max_delta is not None and abs(candidate_value - user_value) > float(max_delta):
            return False, f"{key} tem diferenca maior que o limite."

    return True, None


def explain_match(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
    candidate_name: str,
) -> str:
    user_vectors = normalize_profile_vectors(user_profile)
    candidate_vectors = normalize_profile_vectors(candidate_profile)
    overlaps = _top_shared_interests(user_vectors, candidate_vectors, limit=3)

    if overlaps:
        readable = ", ".join(INTEREST_LABELS.get(key, key).lower() for key, _ in overlaps)
        return f"{candidate_name} combina com voce por interesses fortes em {readable}."

    values = _closest_values(user_vectors, candidate_vectors, limit=2)
    if values:
        readable = ", ".join(VALUE_LABELS.get(key, key).lower() for key, _ in values)
        return f"{candidate_name} parece ter uma sintonia boa em {readable}."

    return f"{candidate_name} apareceu por proximidade vetorial geral entre os perfis."


def public_match_profile(
    candidate_profile: dict[str, Any],
    visible_fields: dict[str, bool] | None = None,
) -> dict[str, Any]:
    return public_profile_from_visibility(candidate_profile, visible_fields)


def fallback_icebreaker(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
    candidate_name: str,
) -> str:
    user_vectors = normalize_profile_vectors(user_profile)
    candidate_vectors = normalize_profile_vectors(candidate_profile)
    overlaps = _top_shared_interests(user_vectors, candidate_vectors, limit=1)

    if overlaps:
        key, _ = overlaps[0]
        label = INTEREST_LABELS.get(key, key).lower()
        return f"Puxa assunto perguntando para {candidate_name} qual foi a experiencia mais marcante dela com {label}."

    values = _closest_values(user_vectors, candidate_vectors, limit=1)
    if values:
        key, _ = values[0]
        label = VALUE_LABELS.get(key, key).lower()
        return f"Comece perguntando como {candidate_name} enxerga {label} no dia a dia."

    return f"Pergunte para {candidate_name} que tipo de conexao faz uma conversa valer a pena."


def generate_icebreaker(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
    candidate_name: str,
) -> str:
    try:
        from src.services.llm_service import gerar_sugestao_assunto_ia

        suggestion = gerar_sugestao_assunto_ia(user_profile, candidate_profile, candidate_name)
        if suggestion:
            return suggestion
    except Exception:
        pass

    return fallback_icebreaker(user_profile, candidate_profile, candidate_name)


def _top_shared_interests(
    user_profile: dict[str, dict[str, float]],
    candidate_profile: dict[str, dict[str, float]],
    limit: int,
) -> list[tuple[str, float]]:
    scores: list[tuple[str, float]] = []
    for key, user_value in user_profile["interesses"].items():
        candidate_value = candidate_profile["interesses"].get(key, 0.5)
        shared_strength = min(user_value, candidate_value)
        if shared_strength >= 0.65:
            distance_penalty = abs(user_value - candidate_value)
            scores.append((key, shared_strength - distance_penalty))

    return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]


def _closest_values(
    user_profile: dict[str, dict[str, float]],
    candidate_profile: dict[str, dict[str, float]],
    limit: int,
) -> list[tuple[str, float]]:
    scores = []
    for key, user_value in user_profile["valores"].items():
        candidate_value = candidate_profile["valores"].get(key, 0.5)
        scores.append((key, abs(user_value - candidate_value)))
    return sorted(scores, key=lambda item: item[1])[:limit]

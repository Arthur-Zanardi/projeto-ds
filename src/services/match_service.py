from __future__ import annotations

import math
from typing import Any

from src.schema.schema_vetores import (
    INTEREST_LABELS,
    PHYSICAL_LABELS,
    PHYSICAL_VECTOR_SCHEMA,
    VALUE_LABELS,
    flatten_base_vectors,
    get_dimension,
    normalize_profile_vectors,
    public_profile_from_visibility,
    top_interests_summary,
    top_physical_matches,
)

NEUTRAL_RELATIONSHIP_VALUES = {"", None, "nao_informar"}
GENDER_TO_INTEREST = {
    "mulher": "mulheres",
    "homem": "homens",
    "nao_binario": "nao_binarias",
}


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
            return False, f"{key} tem diferença maior que o limite."

    return True, None


def relationship_compatible(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
) -> bool:
    user_gender = user_profile.get("gender_identity") or "nao_informar"
    user_interest = user_profile.get("interested_in") or "nao_informar"
    candidate_gender = candidate_profile.get("gender_identity") or "nao_informar"
    candidate_interest = candidate_profile.get("interested_in") or "nao_informar"

    return _interest_accepts_gender(user_interest, candidate_gender) and _interest_accepts_gender(
        candidate_interest,
        user_gender,
    )


def compatibility_breakdown(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
) -> dict[str, Any]:
    user_vectors = normalize_profile_vectors(user_profile)
    candidate_vectors = normalize_profile_vectors(candidate_profile)

    base_similarity = _cosine_similarity(
        flatten_base_vectors(user_vectors),
        flatten_base_vectors(candidate_vectors),
    )
    physical_similarity = _mean_pair_similarity(
        user_vectors["atracao"],
        candidate_vectors["fisico"],
    )
    reciprocal_attraction = _mean_pair_similarity(
        user_vectors["fisico"],
        candidate_vectors["atracao"],
    )
    overall = (
        (0.65 * base_similarity)
        + (0.25 * physical_similarity)
        + (0.10 * reciprocal_attraction)
    )

    return {
        "base_similarity": round(base_similarity * 100, 1),
        "physical_similarity": round(physical_similarity * 100, 1),
        "reciprocal_attraction": round(reciprocal_attraction * 100, 1),
        "overall_affinity": round(overall * 100, 1),
        "top_interests": top_interests_summary(candidate_vectors),
        "physical_matches": top_physical_matches(user_vectors, candidate_vectors),
    }


def explain_match(
    user_profile: dict[str, Any],
    candidate_profile: dict[str, Any],
    candidate_name: str,
) -> str:
    user_vectors = normalize_profile_vectors(user_profile)
    candidate_vectors = normalize_profile_vectors(candidate_profile)
    overlaps = _top_shared_interests(user_vectors, candidate_vectors, limit=3)
    physical = top_physical_matches(user_vectors, candidate_vectors, limit=2)

    fragments: list[str] = []
    if overlaps:
        readable = ", ".join(INTEREST_LABELS.get(key, key).lower() for key, _ in overlaps)
        fragments.append(f"interesses fortes em {readable}")
    if physical:
        readable = ", ".join(item["label"].lower() for item in physical)
        fragments.append(f"preferências em comum, como {readable}")

    if fragments:
        return f"{candidate_name} combina com você por " + " e ".join(fragments) + "."

    values = _closest_values(user_vectors, candidate_vectors, limit=2)
    if values:
        readable = ", ".join(VALUE_LABELS.get(key, key).lower() for key, _ in values)
        return f"{candidate_name} parece ter uma sintonia boa em {readable}."

    return f"{candidate_name} apareceu por uma boa afinidade geral com o seu perfil."


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
        return f"Puxa assunto perguntando para {candidate_name} qual foi a experiência mais marcante dela com {label}."

    physical = top_physical_matches(user_vectors, candidate_vectors, limit=1)
    if physical:
        label = physical[0]["label"].lower()
        return f"Comece elogiando com naturalidade o estilo de {candidate_name}, especialmente {label}, e emende uma pergunta leve."

    values = _closest_values(user_vectors, candidate_vectors, limit=1)
    if values:
        key, _ = values[0]
        label = VALUE_LABELS.get(key, key).lower()
        return f"Comece perguntando como {candidate_name} enxerga {label} no dia a dia."

    return f"Pergunte para {candidate_name} que tipo de conexão faz uma conversa valer a pena."


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


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def _mean_pair_similarity(
    preferences: dict[str, float],
    attributes: dict[str, float],
) -> float:
    scores = []
    for key in PHYSICAL_VECTOR_SCHEMA.keys():
        preference = preferences.get(key, 0.5)
        attribute = attributes.get(key, 0.5)
        if preference == 0.5:
            scores.append(0.5)
        else:
            scores.append(1 - abs(preference - attribute))
    return sum(scores) / len(scores)


def _interest_accepts_gender(interest: str | None, gender: str | None) -> bool:
    if interest in NEUTRAL_RELATIONSHIP_VALUES or interest == "todos":
        return True
    if gender in NEUTRAL_RELATIONSHIP_VALUES:
        return True
    expected = GENDER_TO_INTEREST.get(gender or "")
    if expected is None:
        return True
    return interest == expected

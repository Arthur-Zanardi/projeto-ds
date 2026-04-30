from __future__ import annotations

import unittest

from src.schema.schema_vetores import merge_extracted_profile
from src.services.match_service import (
    compatibility_breakdown,
    fallback_icebreaker,
    passes_value_filters,
    relationship_compatible,
)


class MatchServiceTests(unittest.TestCase):
    def test_value_filter_blocks_large_delta(self) -> None:
        user_profile = {"valores": {"espectro_politico": 0.1}}
        candidate_profile = {"valores": {"espectro_politico": 0.9}}
        filters = [
            {
                "key": "valores.espectro_politico",
                "active": True,
                "max_delta": 0.3,
            }
        ]

        ok, reason = passes_value_filters(user_profile, candidate_profile, filters)

        self.assertFalse(ok)
        self.assertIn("espectro_politico", reason or "")

    def test_value_filter_allows_near_candidate(self) -> None:
        user_profile = {"valores": {"religiosidade": 0.2}}
        candidate_profile = {"valores": {"religiosidade": 0.35}}
        filters = [
            {
                "key": "valores.religiosidade",
                "active": True,
                "max_delta": 0.2,
            }
        ]

        ok, reason = passes_value_filters(user_profile, candidate_profile, filters)

        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_icebreaker_uses_shared_interest(self) -> None:
        user_profile = {"interesses": {"musica": 0.9}}
        candidate_profile = {"interesses": {"musica": 0.8}}

        suggestion = fallback_icebreaker(user_profile, candidate_profile, "Luiza")

        self.assertIn("música", suggestion.lower())
        self.assertIn("Luiza", suggestion)

    def test_compatibility_uses_crossed_physical_vectors(self) -> None:
        user_profile = {
            "atracao": {"olhos_azuis": 1.0},
            "fisico": {"cabelo_preto": 1.0},
            "interesses": {"musica": 0.8},
        }
        candidate_profile = {
            "fisico": {"olhos_azuis": 1.0},
            "atracao": {"cabelo_preto": 1.0},
            "interesses": {"musica": 0.8},
        }

        breakdown = compatibility_breakdown(user_profile, candidate_profile)

        self.assertGreaterEqual(breakdown["physical_similarity"], 50.0)
        self.assertGreaterEqual(breakdown["reciprocal_attraction"], 50.0)
        self.assertGreaterEqual(breakdown["overall_affinity"], 50.0)

    def test_extracted_profile_preserves_physical_questionnaire(self) -> None:
        current = {"fisico": {"olhos_azuis": 1.0}}
        extracted = {
            "fisico": {"olhos_azuis": 0.0},
            "atracao": {"olhos_castanhos": 1.0},
        }

        merged = merge_extracted_profile(current, extracted)

        self.assertEqual(merged["fisico"]["olhos_azuis"], 1.0)
        self.assertEqual(merged["atracao"]["olhos_castanhos"], 1.0)

    def test_relationship_filter_blocks_when_interests_do_not_match(self) -> None:
        user_profile = {"gender_identity": "homem", "interested_in": "mulheres"}
        candidate_profile = {"gender_identity": "homem", "interested_in": "mulheres"}

        self.assertFalse(relationship_compatible(user_profile, candidate_profile))

    def test_relationship_filter_allows_neutral_or_everyone(self) -> None:
        user_profile = {"gender_identity": "homem", "interested_in": "todos"}
        candidate_profile = {"gender_identity": "mulher", "interested_in": "nao_informar"}

        self.assertTrue(relationship_compatible(user_profile, candidate_profile))


if __name__ == "__main__":
    unittest.main()

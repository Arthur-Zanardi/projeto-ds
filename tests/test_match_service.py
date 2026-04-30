from __future__ import annotations

import unittest

from src.services.match_service import fallback_icebreaker, passes_value_filters


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

        self.assertIn("musica", suggestion.lower())
        self.assertIn("Luiza", suggestion)


if __name__ == "__main__":
    unittest.main()

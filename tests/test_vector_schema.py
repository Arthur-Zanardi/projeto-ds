from __future__ import annotations

import unittest

from src.schema.schema_vetores import (
    PHYSICAL_VECTOR_SCHEMA,
    QUERY_VECTOR_ORDER,
    STORAGE_VECTOR_ORDER,
    VECTOR_ORDER,
    flatten_query_vectors,
    flatten_profile_vectors,
    normalize_profile_vectors,
    vector_to_profile,
)


class VectorSchemaTests(unittest.TestCase):
    def test_flatten_order_is_stable(self) -> None:
        profile = normalize_profile_vectors(
            {
                "psicologico": {"extroversao": 1.0},
                "valores": {"espectro_politico": 0.2},
                "interesses": {"animes": 0.9},
            }
        )

        vector = flatten_profile_vectors(profile)

        self.assertEqual(len(vector), len(VECTOR_ORDER))
        self.assertEqual(vector[VECTOR_ORDER.index(("psicologico", "extroversao"))], 1.0)
        self.assertEqual(vector[VECTOR_ORDER.index(("valores", "espectro_politico"))], 0.2)
        self.assertEqual(vector[VECTOR_ORDER.index(("interesses", "animes"))], 0.9)

    def test_missing_and_invalid_values_default_to_half(self) -> None:
        profile = normalize_profile_vectors({"interesses": {"musica": "muito"}})

        self.assertEqual(profile["interesses"]["musica"], 0.5)
        self.assertEqual(profile["valores"]["religiosidade"], 0.5)
        self.assertEqual(profile["fisico"]["olhos_azuis"], 0.5)
        self.assertEqual(profile["atracao"]["olhos_azuis"], 0.5)

    def test_vector_round_trip(self) -> None:
        vector = [0.1] * len(VECTOR_ORDER)
        profile = vector_to_profile(vector)

        self.assertEqual(flatten_profile_vectors(profile), vector)

    def test_storage_and_query_vectors_cross_physical_attraction(self) -> None:
        profile = normalize_profile_vectors(
            {
                "fisico": {"olhos_azuis": 1.0},
                "atracao": {"olhos_castanhos": 1.0},
            }
        )

        storage = flatten_profile_vectors(profile)
        query = flatten_query_vectors(profile)

        self.assertEqual(len(storage), len(STORAGE_VECTOR_ORDER))
        self.assertEqual(len(query), len(QUERY_VECTOR_ORDER))
        self.assertEqual(
            storage[STORAGE_VECTOR_ORDER.index(("fisico", "olhos_azuis"))],
            1.0,
        )
        self.assertEqual(
            query[QUERY_VECTOR_ORDER.index(("atracao", "olhos_castanhos"))],
            1.0,
        )
        self.assertEqual(len(PHYSICAL_VECTOR_SCHEMA), 17)


if __name__ == "__main__":
    unittest.main()

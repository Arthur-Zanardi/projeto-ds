"""Teste da busca vetorial com pgvector + afinidade mascarada."""
from src.services import database


def test_busca_pgvector_prioriza_perfil_parecido(db):
    base = {
        "psicologico": {
            "extroversao": 0.9,
            "abertura_experiencias": 0.9,
            "romantismo_afeto": 0.9,
            "ritmo_vida": 0.9,
        },
        "valores": {},
        "interesses": {},
    }
    diferente = {
        "psicologico": {
            "extroversao": 0.1,
            "abertura_experiencias": 0.1,
            "romantismo_afeto": 0.1,
            "ritmo_vida": 0.1,
        },
        "valores": {},
        "interesses": {},
    }
    database.salvar_perfil_vetorial("cand_parecido", "Parecido", base)
    database.salvar_perfil_vetorial("cand_diferente", "Diferente", diferente)

    vetor_usuario = database.achatar_dados_vetoriais(base)
    resultados = database.buscar_melhor_match("user_busca", vetor_usuario, quantidade=2)

    assert resultados, "deveria retornar candidatos"
    assert resultados[0]["id"] == "cand_parecido"
    afinidades = {r["id"]: float(r["afinidade"].rstrip("%")) for r in resultados}
    assert afinidades["cand_parecido"] > afinidades["cand_diferente"]


def test_busca_ignora_o_proprio_usuario(db):
    perfil = {"psicologico": {"extroversao": 0.8, "ritmo_vida": 0.8, "romantismo_afeto": 0.8}, "valores": {}, "interesses": {}}
    database.salvar_perfil_vetorial("user_busca", "Eu", perfil)
    database.salvar_perfil_vetorial("outro", "Outro", perfil)
    vetor = database.achatar_dados_vetoriais(perfil)
    ids = [r["id"] for r in database.buscar_melhor_match("user_busca", vetor, quantidade=5)]
    assert "user_busca" not in ids
    assert "outro" in ids

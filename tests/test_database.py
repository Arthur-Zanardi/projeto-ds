"""Testes das funções puras da camada vetorial (sem banco)."""
from src.services import database


def test_achatar_dados_vetoriais_usa_indices_corretos():
    dados = {
        "psicologico": {"extroversao": 0.8},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 1.0},
    }
    vetor = database.achatar_dados_vetoriais(dados)
    dims = database.dimensoes_schema_vetorial()
    assert len(vetor) == len(dims) == 34
    assert vetor[dims.index(("psicologico", "extroversao"))] == 0.8
    assert vetor[dims.index(("valores", "religiosidade"))] == 0.2
    assert vetor[dims.index(("interesses", "musica"))] == 1.0
    assert vetor[dims.index(("interesses", "filmes"))] == 0.5  # ausente -> neutro


def test_afinidade_mascarada_ignora_neutros():
    n = len(database.dimensoes_schema_vetorial())
    u = [0.5] * n
    c = [0.5] * n
    assert database.calcular_afinidade_mascarada(u, c) is None  # < 3 pares com sinal
    for i in range(3):
        u[i] = 0.8
        c[i] = 0.8
    resultado = database.calcular_afinidade_mascarada(u, c)
    assert resultado is not None
    assert resultado["afinidade"] == 100.0
    assert resultado["dimensoes_comparadas"] == 3


def test_afinidade_cai_com_diferenca():
    n = len(database.dimensoes_schema_vetorial())
    u = [0.5] * n
    c = [0.5] * n
    for i in range(3):
        u[i] = 0.9
        c[i] = 0.1
    assert database.calcular_afinidade_mascarada(u, c)["afinidade"] < 50


def test_criar_vetor_mock_padrao_deterministico():
    a = database.criar_vetor_mock_padrao("user_lia")
    b = database.criar_vetor_mock_padrao("user_lia")
    assert a == b
    assert set(a.keys()) == {"psicologico", "valores", "interesses"}


def test_dimensoes_mais_proximas_ordena_por_diferenca():
    n = len(database.dimensoes_schema_vetorial())
    u = [0.5] * n
    c = [0.5] * n
    u[0], c[0] = 0.80, 0.79  # quase iguais
    u[1], c[1] = 0.90, 0.10  # bem diferentes
    proximas = database.calcular_dimensoes_mais_proximas(u, c, quantidade=2)
    assert proximas[0]["diferenca"] <= proximas[1]["diferenca"]

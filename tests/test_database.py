from src.services import database


class ColecaoFake:
    def __init__(self, resultado_query=None, resultado_get=None):
        self.upserts = []
        self.resultado_query = resultado_query
        self.resultado_get = resultado_get or {"ids": []}
        self.query_kwargs = None

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def get(self):
        return self.resultado_get

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return self.resultado_query


def test_salvar_perfil_usuario_transforma_json_em_vetor(monkeypatch):
    colecao = ColecaoFake()
    monkeypatch.setattr(database, "colecao_usuarios", colecao)
    dados = {
        "psicologico": {"extroversao": 0.8},
        "valores": {"religiosidade": 0.2},
        "interesses": {"musica": 1.0},
    }

    vetor = database.salvar_perfil_usuario("user_1", "Ana", dados)

    assert vetor == [0.8, 0.2, 1.0]
    assert colecao.upserts == [
        {
            "ids": ["user_1"],
            "embeddings": [[0.8, 0.2, 1.0]],
            "metadatas": [{"nome": "Ana"}],
            "documents": ["Perfil de Ana"],
        }
    ]


def test_calcular_afinidade_mascarada_ignora_05_dos_dois_lados():
    resultado = database.calcular_afinidade_mascarada(
        [0.5, 0.64, 0.96, 0.2, 0.4],
        [0.1, 0.60, 0.86, 0.5, 0.7],
    )

    assert resultado == {
        "afinidade": 85.3,
        "distancia_matematica": 0.1467,
        "dimensoes_comparadas": 3,
    }


def test_calcular_afinidade_mascarada_exige_minimo_de_dimensoes():
    resultado = database.calcular_afinidade_mascarada(
        [0.5, 0.64, 0.96],
        [0.1, 0.60, 0.5],
    )

    assert resultado is None


def test_buscar_melhor_match_recalcula_afinidade_mascarada(monkeypatch):
    colecao = ColecaoFake(
        resultado_query={
            "ids": [["user_rafaell", "user_maria"]],
            "embeddings": [[
                [0.5, 0.64, 0.96, 0.2, 0.4],
                [0.1, 0.60, 0.86, 0.5, 0.7],
            ]],
            "distances": [[0.0, 0.18]],
            "metadatas": [[{"nome": "Rafaell"}, {"nome": "Maria"}]],
        }
    )
    monkeypatch.setattr(database, "colecao_usuarios", colecao)

    resultado = database.buscar_melhor_match(
        "user_rafaell",
        [0.5, 0.64, 0.96, 0.2, 0.4],
        quantidade=1,
    )

    assert colecao.query_kwargs == {
        "query_embeddings": [[0.5, 0.64, 0.96, 0.2, 0.4]],
        "n_results": 5,
        "include": ["embeddings", "metadatas", "distances"],
    }
    assert resultado == [
        {
            "id": "user_maria",
            "nome": "Maria",
            "afinidade": "85.3%",
            "distancia_matematica": 0.1467,
            "dimensoes_comparadas": 3,
        }
    ]


def test_buscar_melhor_match_descarta_candidato_sem_dimensoes_suficientes(monkeypatch):
    colecao = ColecaoFake(
        resultado_query={
            "ids": [["user_carmen"]],
            "embeddings": [[[0.1, 0.60, 0.5]]],
            "distances": [[0.2]],
            "metadatas": [[{"nome": "Carmen"}]],
        }
    )
    monkeypatch.setattr(database, "colecao_usuarios", colecao)

    resultado = database.buscar_melhor_match(
        "user_rafaell",
        [0.5, 0.64, 0.96],
        quantidade=1,
    )

    assert resultado == []


def test_buscar_melhor_match_ignora_usuario_legado_do_admin(monkeypatch):
    colecao = ColecaoFake(
        resultado_query={
            "ids": [["user_rafaell", "user_maria"]],
            "embeddings": [[
                [0.1, 0.60, 0.86, 0.5, 0.7],
                [0.1, 0.60, 0.86, 0.5, 0.7],
            ]],
            "distances": [[0.01, 0.02]],
            "metadatas": [[{"nome": "Rafaell"}, {"nome": "Maria"}]],
        }
    )
    monkeypatch.setattr(database, "colecao_usuarios", colecao)

    resultado = database.buscar_melhor_match(
        "rafaellapipucos@gmail.com",
        [0.5, 0.64, 0.96, 0.2, 0.4],
        quantidade=1,
    )

    assert resultado == [
        {
            "id": "user_maria",
            "nome": "Maria",
            "afinidade": "85.3%",
            "distancia_matematica": 0.1467,
            "dimensoes_comparadas": 3,
        }
    ]


def test_popular_banco_mock_cria_mocks_faltantes_mesmo_com_banco_existente(monkeypatch):
    colecao = ColecaoFake(resultado_get={"ids": ["user_rafaell", "user_maria"]})
    monkeypatch.setattr(database, "colecao_usuarios", colecao)

    database.popular_banco_mock()

    assert [upsert["ids"] for upsert in colecao.upserts] == [["user_carmen"]]

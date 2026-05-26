from src.services import database


class ColecaoFake:
    def __init__(self, resultado_query=None):
        self.upserts = []
        self.resultado_query = resultado_query
        self.query_kwargs = None

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

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


def test_buscar_melhor_match_ignora_proprio_usuario(monkeypatch):
    colecao = ColecaoFake(
        resultado_query={
            "ids": [["user_rafaell", "user_maria"]],
            "distances": [[0.0, 0.18]],
            "metadatas": [[{"nome": "Rafaell"}, {"nome": "Maria"}]],
        }
    )
    monkeypatch.setattr(database, "colecao_usuarios", colecao)

    resultado = database.buscar_melhor_match(
        "user_rafaell",
        [0.5, 0.5],
        quantidade=1,
    )

    assert colecao.query_kwargs == {
        "query_embeddings": [[0.5, 0.5]],
        "n_results": 2,
    }
    assert resultado == [
        {
            "id": "user_maria",
            "nome": "Maria",
            "afinidade": "82.0%",
            "distancia_matematica": 0.18,
        }
    ]

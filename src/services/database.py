import hashlib

from src.schema.schema_vetores import (
    VetorInteresses,
    VetorPsicologico,
    VetorValores,
)
from src.services.user_context import (
    EMAIL_USUARIO_PADRAO,
    USUARIO_LEGADO,
    normalizar_email_usuario,
)


VALOR_NEUTRO = 0.5
MINIMO_DIMENSOES_COMPARADAS = 3

colecao_usuarios = None


def obter_colecao_usuarios():
    global colecao_usuarios

    if colecao_usuarios is None:
        import chromadb

        chroma_client = chromadb.PersistentClient(path="./banco_vetorial")
        colecao_usuarios = chroma_client.get_or_create_collection(
            name="perfis_matchai",
            metadata={"hnsw:space": "cosine"},
        )

    return colecao_usuarios


def dimensoes_schema_vetorial():
    grupos = [
        ("psicologico", VetorPsicologico),
        ("valores", VetorValores),
        ("interesses", VetorInteresses),
    ]
    dimensoes = []

    for grupo, modelo in grupos:
        for campo in modelo.model_fields:
            dimensoes.append((grupo, campo))

    return dimensoes


def _valor_vetorial(dados: dict, grupo: str, campo: str):
    try:
        return round(float(dados.get(grupo, {}).get(campo, VALOR_NEUTRO)), 2)
    except (TypeError, ValueError):
        return VALOR_NEUTRO


def achatar_dados_vetoriais(dados_extraidos_ia: dict):
    return [
        _valor_vetorial(dados_extraidos_ia or {}, grupo, campo)
        for grupo, campo in dimensoes_schema_vetorial()
    ]


def vetor_para_dict(vetor: list[float]):
    resultado = {"psicologico": {}, "valores": {}, "interesses": {}}

    for indice, (grupo, campo) in enumerate(dimensoes_schema_vetorial()):
        valor = vetor[indice] if indice < len(vetor) else VALOR_NEUTRO
        resultado[grupo][campo] = round(float(valor), 2)

    return resultado


def criar_vetor_mock_padrao(seed: str):
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    valores = []

    for indice, _ in enumerate(dimensoes_schema_vetorial()):
        byte = digest[indice % len(digest)]
        valor = 0.18 + (byte / 255) * 0.68
        valores.append(round(valor, 2))

    return vetor_para_dict(valores)


def calcular_afinidade_mascarada(
    vetor_usuario: list,
    vetor_candidato: list,
    minimo_dimensoes: int = MINIMO_DIMENSOES_COMPARADAS,
):
    pares_validos = []

    for valor_usuario, valor_candidato in zip(vetor_usuario, vetor_candidato):
        valor_usuario = round(float(valor_usuario), 2)
        valor_candidato = round(float(valor_candidato), 2)

        if valor_usuario == VALOR_NEUTRO or valor_candidato == VALOR_NEUTRO:
            continue

        pares_validos.append((valor_usuario, valor_candidato))

    if len(pares_validos) < minimo_dimensoes:
        return None

    diferencas = [
        abs(valor_usuario - valor_candidato)
        for valor_usuario, valor_candidato in pares_validos
    ]
    distancia_media = round(sum(diferencas) / len(diferencas), 4)
    afinidade = round((1 - distancia_media) * 100, 1)

    return {
        "afinidade": afinidade,
        "distancia_matematica": distancia_media,
        "dimensoes_comparadas": len(pares_validos),
    }


def calcular_dimensoes_mais_proximas(
    vetor_usuario: list,
    vetor_candidato: list,
    quantidade: int = 3,
):
    proximas = []

    for indice, (grupo, campo) in enumerate(dimensoes_schema_vetorial()):
        if indice >= len(vetor_usuario) or indice >= len(vetor_candidato):
            continue

        valor_usuario = round(float(vetor_usuario[indice]), 2)
        valor_candidato = round(float(vetor_candidato[indice]), 2)
        diferenca = round(abs(valor_usuario - valor_candidato), 4)
        tem_sinal = valor_usuario != VALOR_NEUTRO or valor_candidato != VALOR_NEUTRO

        proximas.append({
            "grupo": grupo,
            "campo": campo,
            "rotulo": campo.replace("_", " ").title(),
            "diferenca": diferenca,
            "valor_usuario": valor_usuario,
            "valor_candidato": valor_candidato,
            "tem_sinal": tem_sinal,
        })

    proximas.sort(key=lambda item: (not item["tem_sinal"], item["diferenca"], item["campo"]))
    return proximas[:quantidade]


def salvar_perfil_usuario(id_usuario: str, nome: str, dados_extraidos_ia: dict):
    """
    Transforma o JSON extraido pela IA em uma lista de floats e salva no ChromaDB.
    """
    id_usuario = normalizar_email_usuario(id_usuario)
    vetor_usuario = achatar_dados_vetoriais(dados_extraidos_ia)

    colecao = obter_colecao_usuarios()
    colecao.upsert(
        ids=[id_usuario],
        embeddings=[vetor_usuario],
        metadatas=[{"nome": nome}],
        documents=[f"Perfil de {nome}"],
    )

    print(
        f"Perfil de {nome} salvo com sucesso! "
        f"Tamanho do vetor: {len(vetor_usuario)} dimensoes."
    )
    return vetor_usuario


def salvar_perfil_vetorial(id_usuario: str, nome: str, vetor_dict: dict):
    vetor_usuario = achatar_dados_vetoriais(vetor_dict)
    colecao = obter_colecao_usuarios()
    colecao.upsert(
        ids=[id_usuario],
        embeddings=[vetor_usuario],
        metadatas=[{"nome": nome}],
        documents=[f"Perfil de {nome}"],
    )
    return vetor_usuario


def obter_vetor_usuario(id_usuario: str):
    colecao = obter_colecao_usuarios()
    resultado = colecao.get(ids=[id_usuario], include=["embeddings", "metadatas"])
    embeddings = resultado.get("embeddings")

    if embeddings is None or len(embeddings) == 0:
        return None

    vetor = embeddings[0]
    if vetor is None or len(vetor) == 0:
        return None

    return [float(valor) for valor in vetor]


def buscar_melhor_match(
    id_usuario_buscando: str,
    vetor_do_usuario: list,
    quantidade: int = 1,
    ids_ignorados: set[str] | None = None,
    incluir_vetor: bool = False,
):
    """
    Busca candidatos no ChromaDB e recalcula a afinidade ignorando valores 0.5.
    """
    id_usuario_buscando = normalizar_email_usuario(id_usuario_buscando)
    colecao = obter_colecao_usuarios()
    resultados = colecao.query(
        query_embeddings=[vetor_do_usuario],
        n_results=max(quantidade * 8, quantidade + 4),
        include=["embeddings", "metadatas", "distances"],
    )

    ids_encontrados = resultados.get("ids", [[]])[0]
    embeddings_encontrados = resultados.get("embeddings", [[]])[0]
    metadados_encontrados = resultados.get("metadatas", [[]])[0]
    matches_reais = []
    ids_para_ignorar = {id_usuario_buscando, *(ids_ignorados or set())}

    if normalizar_email_usuario(id_usuario_buscando) == EMAIL_USUARIO_PADRAO:
        ids_para_ignorar.add(USUARIO_LEGADO)

    for indice, id_encontrado in enumerate(ids_encontrados):
        if id_encontrado in ids_para_ignorar:
            continue

        if indice >= len(embeddings_encontrados):
            continue

        vetor_candidato = [float(valor) for valor in embeddings_encontrados[indice]]
        afinidade_calculada = calcular_afinidade_mascarada(
            vetor_do_usuario,
            vetor_candidato,
        )

        if afinidade_calculada is None:
            continue

        metadados = (
            metadados_encontrados[indice]
            if indice < len(metadados_encontrados)
            else {}
        )
        match = {
            "id": id_encontrado,
            "nome": metadados.get("nome", "Desconhecido"),
            "afinidade": f"{afinidade_calculada['afinidade']}%",
            "score_interno": afinidade_calculada["afinidade"],
            "distancia_matematica": afinidade_calculada["distancia_matematica"],
            "dimensoes_comparadas": afinidade_calculada["dimensoes_comparadas"],
        }

        if incluir_vetor:
            match["vetor_candidato"] = vetor_candidato

        matches_reais.append(match)

    matches_reais.sort(key=lambda match: match["score_interno"], reverse=True)
    if not incluir_vetor:
        for match in matches_reais:
            match.pop("score_interno", None)

    return matches_reais[:quantidade]


def popular_banco_mock():
    colecao = obter_colecao_usuarios()
    resultados = colecao.get()
    ids_existentes = set(resultados.get("ids", []))

    perfis_mock = [
        (
            "user_maria",
            "Maria",
            22,
            "Recife, PE",
            "Estudante de Tecnologia",
            "Curiosa por tecnologia, cafeterias escondidas e conversas que pulam de animes para planos de viagem.",
            "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=900&h=1200&fit=crop",
            {
                "psicologico": {
                    "extroversao": 0.6,
                    "abertura_experiencias": 0.6,
                    "romantismo_afeto": 0.5,
                    "ritmo_vida": 0.6,
                    "logica_vs_emocao": 0.7,
                    "resolucao_conflitos": 0.5,
                    "competitividade_cooperacao": 0.5,
                },
                "valores": {
                    "ambicao_carreira": 0.6,
                    "conservadorismo": 0.4,
                    "espectro_politico": 0.5,
                    "gestao_financeira": 0.6,
                    "religiosidade": 0.4,
                    "gosto_festas": 0.6,
                },
                "interesses": {
                    "animes": 0.9,
                    "filmes": 0.6,
                    "series": 0.7,
                    "livros_ficcao": 0.8,
                    "videogames": 0.7,
                    "jogos_tabuleiro": 0.4,
                    "tecnologia": 0.6,
                    "academia": 0.8,
                    "esportes": 0.8,
                    "futebol": 0.9,
                    "dancas": 0.3,
                    "musica": 0.6,
                    "tocar_instrumentos": 0.2,
                    "fotografia": 0.4,
                    "culinaria": 0.6,
                    "idiomas": 0.6,
                    "celebridades": 0.2,
                    "historia": 0.5,
                    "geografia": 0.4,
                    "geopolitica": 0.5,
                    "astronomia": 0.5,
                },
            },
        ),
        (
            "user_carmen",
            "Carmen",
            24,
            "Olinda, PE",
            "Designer",
            "Designer tranquila, apaixonada por musica, cozinhar no fim de semana e encontrar beleza nas pequenas rotinas.",
            "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=900&h=1200&fit=crop",
            {
                "psicologico": {
                    "extroversao": 0.2,
                    "abertura_experiencias": 0.2,
                    "romantismo_afeto": 0.8,
                    "ritmo_vida": 0.2,
                    "logica_vs_emocao": 0.2,
                    "resolucao_conflitos": 0.2,
                    "competitividade_cooperacao": 0.2,
                },
                "valores": {
                    "ambicao_carreira": 0.2,
                    "conservadorismo": 1.0,
                    "espectro_politico": 0.9,
                    "gestao_financeira": 0.2,
                    "religiosidade": 1.0,
                    "gosto_festas": 0.0,
                },
                "interesses": {
                    "animes": 0.0,
                    "filmes": 0.2,
                    "series": 0.2,
                    "livros_ficcao": 0.1,
                    "videogames": 0.0,
                    "jogos_tabuleiro": 0.1,
                    "tecnologia": 0.1,
                    "academia": 0.0,
                    "esportes": 0.0,
                    "futebol": 0.0,
                    "dancas": 0.1,
                    "musica": 0.5,
                    "tocar_instrumentos": 0.0,
                    "fotografia": 0.1,
                    "culinaria": 0.8,
                    "idiomas": 0.1,
                    "celebridades": 0.8,
                    "historia": 0.2,
                    "geografia": 0.2,
                    "geopolitica": 0.1,
                    "astronomia": 0.0,
                },
            },
        ),
        (
            "user_lia",
            "Lia",
            21,
            "Joao Pessoa, PB",
            "Fotografa",
            "Fotografa de rua, fa de trilhas curtas, playlists enormes e gente que sabe rir de um dia estranho.",
            "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=900&h=1200&fit=crop",
            criar_vetor_mock_padrao("user_lia"),
        ),
    ]

    perfis_faltantes = [perfil for perfil in perfis_mock if perfil[0] not in ids_existentes]

    if perfis_faltantes:
        print("Populando banco com perfis de teste...")
        for id_usuario, nome, *_rest, perfil in perfis_faltantes:
            salvar_perfil_vetorial(id_usuario, nome, perfil)
        print("Perfis de teste criados!")

    try:
        from src.services.sqlite_db import salvar_perfil_publico

        for (
            id_usuario,
            nome,
            idade,
            localizacao,
            cargo,
            descricao,
            foto_url,
            _perfil,
        ) in perfis_mock:
            salvar_perfil_publico(
                usuario=id_usuario,
                nome=nome,
                idade=idade,
                foto_url=foto_url,
                descricao=descricao,
                localizacao=localizacao,
                cargo=cargo,
                origem="mock",
                mock_customizado=False,
            )
    except Exception:
        # A API tambem inicializa o SQLite; mocks vetoriais nao devem falhar por isso.
        pass

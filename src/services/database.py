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


def achatar_dados_vetoriais(dados_extraidos_ia: dict):
    psicologico = dados_extraidos_ia.get("psicologico", {})
    valores = dados_extraidos_ia.get("valores", {})
    interesses = dados_extraidos_ia.get("interesses", {})

    return (
        list(psicologico.values()) +
        list(valores.values()) +
        list(interesses.values())
    )


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


def salvar_perfil_usuario(id_usuario: str, nome: str, dados_extraidos_ia: dict):
    """
    Transforma o JSON extraido pela IA em uma lista de floats e salva no ChromaDB.
    """
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


def buscar_melhor_match(
    id_usuario_buscando: str,
    vetor_do_usuario: list,
    quantidade: int = 1,
):
    """
    Busca candidatos no ChromaDB e recalcula a afinidade ignorando valores 0.5.
    """
    colecao = obter_colecao_usuarios()
    resultados = colecao.query(
        query_embeddings=[vetor_do_usuario],
        n_results=max(quantidade * 5, quantidade + 1),
        include=["embeddings", "metadatas", "distances"],
    )

    ids_encontrados = resultados.get("ids", [[]])[0]
    embeddings_encontrados = resultados.get("embeddings", [[]])[0]
    metadados_encontrados = resultados.get("metadatas", [[]])[0]
    matches_reais = []

    for i, id_encontrado in enumerate(ids_encontrados):
        if id_encontrado == id_usuario_buscando:
            continue

        if i >= len(embeddings_encontrados):
            continue

        afinidade_calculada = calcular_afinidade_mascarada(
            vetor_do_usuario,
            embeddings_encontrados[i],
        )

        if afinidade_calculada is None:
            continue

        metadados = (
            metadados_encontrados[i]
            if i < len(metadados_encontrados)
            else {}
        )

        matches_reais.append({
            "id": id_encontrado,
            "nome": metadados.get("nome", "Desconhecido"),
            "afinidade": f"{afinidade_calculada['afinidade']}%",
            "distancia_matematica": afinidade_calculada["distancia_matematica"],
            "dimensoes_comparadas": afinidade_calculada["dimensoes_comparadas"],
        })

    matches_reais.sort(
        key=lambda match: float(match["afinidade"].replace("%", "")),
        reverse=True,
    )

    return matches_reais[:quantidade]


def popular_banco_mock():
    colecao = obter_colecao_usuarios()
    resultados = colecao.get()

    if len(resultados["ids"]) > 0:
        return

    print("Populando banco com perfis de teste...")

    perfil_maria = {
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
    }

    perfil_carmen = {
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
    }

    salvar_perfil_usuario("user_maria", "Maria", perfil_maria)
    salvar_perfil_usuario("user_carmen", "Carmen", perfil_carmen)
    print("Perfis de teste criados!")

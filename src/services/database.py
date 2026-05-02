import chromadb
from chromadb.config import Settings

# 1. Inicializa o cliente para salvar os dados numa pasta chamada "banco_vetorial"
chroma_client = chromadb.PersistentClient(path="./banco_vetorial")

# 2. Cria (ou carrega) a coleção (tabela) onde os usuários vão morar.
# Usamos o espaço "cosine" (Similaridade de Cossenos), que é o padrão ouro na matemática para comparar perfis psicológicos e interesses.
colecao_usuarios = chroma_client.get_or_create_collection(
    name="perfis_matchai",
    metadata={"hnsw:space": "cosine"} 
)

def salvar_perfil_usuario(id_usuario: str, nome: str, dados_extraidos_ia: dict):
    """
    Transforma o JSON extraído pela IA em uma lista reta (embedding) e salva no banco.
    """
    # 1. Extraímos os blocos do JSON (que vieram da sua função extrair_vetores_da_conversa)
    psicologico = dados_extraidos_ia.get("psicologico", {})
    valores = dados_extraidos_ia.get("valores", {})
    interesses = dados_extraidos_ia.get("interesses", {})

    # 2. Achata tudo em uma única lista gigante de números flutuantes (O "Vetor")
    vetor_usuario = (
        list(psicologico.values()) +
        list(valores.values()) +
        list(interesses.values())
    )

    # 3. Salva no ChromaDB
    colecao_usuarios.upsert(
        ids=[id_usuario],
        embeddings=[vetor_usuario],
        metadatas=[{"nome": nome}], # Aqui você pode adicionar idade, cidade, etc.
        documents=[f"Perfil de {nome}"] 
    )
    
    print(f"✅ Perfil de {nome} salvo com sucesso! Tamanho do vetor: {len(vetor_usuario)} dimensões.")
    return vetor_usuario

def buscar_melhor_match(id_usuario_buscando: str, vetor_do_usuario: list, quantidade: int = 1):
    """
    Busca no banco de dados a pessoa com o vetor mais próximo (menor distância).
    """
    resultados = colecao_usuarios.query(
        query_embeddings=[vetor_do_usuario],
        n_results=quantidade + 1, # Pedimos +1 porque o sistema vai achar o próprio usuário!
    )
    
    # Precisamos filtrar para não dar match da pessoa com ela mesma
    matches_reais = []
    
    for i in range(len(resultados['ids'][0])):
        id_encontrado = resultados['ids'][0][i]
        
        # Ignora se o banco devolver o próprio usuário que está buscando
        if id_encontrado == id_usuario_buscando:
            continue
            
        # Pega a distância (quanto mais perto de 0, mais parecido, pois usamos cosine distance)
        distancia = resultados['distances'][0][i]
        afinidade_porcentagem = round((1 - distancia) * 100, 1)
        
        metadados = resultados['metadatas'][0][i]
        
        matches_reais.append({
            "id": id_encontrado,
            "nome": metadados.get("nome", "Desconhecido"),
            "afinidade": f"{afinidade_porcentagem}%",
            "distancia_matematica": distancia
        })
        
        # Se já achou a quantidade que queríamos (ex: top 1), para o loop
        if len(matches_reais) == quantidade:
            break

    return matches_reais

def popular_banco_mock():
    # Cria os perfis de teste caso o banco esteja vazio
    resultados = colecao_usuarios.get()
    if len(resultados['ids']) == 0:
        print("Populando banco com perfis de teste...")
        
        perfil_maria = {
            "psicologico": {"extroversao": 0.6, "abertura_experiencias": 0.6, "romantismo_afeto": 0.5, "ritmo_vida": 0.6, "logica_vs_emocao": 0.7, "resolucao_conflitos": 0.5, "competitividade_cooperacao": 0.5},
            "valores": {"ambicao_carreira": 0.6, "conservadorismo": 0.4, "espectro_politico": 0.5, "gestao_financeira": 0.6, "religiosidade": 0.4, "gosto_festas": 0.6},
            "interesses": {"animes": 0.9, "filmes": 0.6, "series": 0.7, "livros_ficcao": 0.8, "videogames": 0.7, "jogos_tabuleiro": 0.4, "tecnologia": 0.6, "academia": 0.8, "esportes": 0.8, "futebol": 0.9, "dancas": 0.3, "musica": 0.6, "tocar_instrumentos": 0.2, "fotografia": 0.4, "culinaria": 0.6, "idiomas": 0.6, "celebridades": 0.2, "historia": 0.5, "geografia": 0.4, "geopolitica": 0.5, "astronomia": 0.5}
        }

        perfil_carmen = {
            "psicologico": {"extroversao": 0.2, "abertura_experiencias": 0.2, "romantismo_afeto": 0.8, "ritmo_vida": 0.2, "logica_vs_emocao": 0.2, "resolucao_conflitos": 0.2, "competitividade_cooperacao": 0.2},
            "valores": {"ambicao_carreira": 0.2, "conservadorismo": 1.0, "espectro_politico": 0.9, "gestao_financeira": 0.2, "religiosidade": 1.0, "gosto_festas": 0.0},
            "interesses": {"animes": 0.0, "filmes": 0.2, "series": 0.2, "livros_ficcao": 0.1, "videogames": 0.0, "jogos_tabuleiro": 0.1, "tecnologia": 0.1, "academia": 0.0, "esportes": 0.0, "futebol": 0.0, "dancas": 0.1, "musica": 0.5, "tocar_instrumentos": 0.0, "fotografia": 0.1, "culinaria": 0.8, "idiomas": 0.1, "celebridades": 0.8, "historia": 0.2, "geografia": 0.2, "geopolitica": 0.1, "astronomia": 0.0}
        }
        salvar_perfil_usuario("user_maria", "Maria", perfil_maria)
        salvar_perfil_usuario("user_carmen", "Carmen", perfil_carmen)
        print("Perfis de teste criados!")

# --- ÁREA DE TESTE ---
if __name__ == "__main__":
    
    # 1. O seu perfil (Exatamente como a API gerou)
    perfil_rafaell = {
        "psicologico": {"extroversao": 0.5, "abertura_experiencias": 0.5, "romantismo_afeto": 0.5, "ritmo_vida": 0.5, "logica_vs_emocao": 0.6, "resolucao_conflitos": 0.5, "competitividade_cooperacao": 0.6},
        "valores": {"ambicao_carreira": 0.5, "conservadorismo": 0.5, "espectro_politico": 0.5, "gestao_financeira": 0.5, "religiosidade": 0.5, "gosto_festas": 0.5},
        "interesses": {"animes": 1.0, "filmes": 0.5, "series": 0.5, "livros_ficcao": 0.5, "videogames": 0.5, "jogos_tabuleiro": 0.5, "tecnologia": 0.5, "academia": 0.7, "esportes": 0.7, "futebol": 1.0, "dancas": 0.5, "musica": 0.5, "tocar_instrumentos": 0.5, "fotografia": 0.5, "culinaria": 0.5, "idiomas": 0.5, "celebridades": 0.5, "historia": 0.5, "geografia": 0.5, "geopolitica": 0.5, "astronomia": 0.5}
    }

    # 2. Perfil de uma garota compatível (Também adora animes, futebol e academia)
    perfil_maria = {
        "psicologico": {"extroversao": 0.6, "abertura_experiencias": 0.6, "romantismo_afeto": 0.5, "ritmo_vida": 0.6, "logica_vs_emocao": 0.7, "resolucao_conflitos": 0.5, "competitividade_cooperacao": 0.5},
        "valores": {"ambicao_carreira": 0.6, "conservadorismo": 0.4, "espectro_politico": 0.5, "gestao_financeira": 0.6, "religiosidade": 0.4, "gosto_festas": 0.6},
        "interesses": {"animes": 0.9, "filmes": 0.6, "series": 0.7, "livros_ficcao": 0.8, "videogames": 0.7, "jogos_tabuleiro": 0.4, "tecnologia": 0.6, "academia": 0.8, "esportes": 0.8, "futebol": 0.9, "dancas": 0.3, "musica": 0.6, "tocar_instrumentos": 0.2, "fotografia": 0.4, "culinaria": 0.6, "idiomas": 0.6, "celebridades": 0.2, "historia": 0.5, "geografia": 0.4, "geopolitica": 0.5, "astronomia": 0.5}
    }

    # 3. Perfil totalmente incompatível (Odeia animes, esportes e futebol, totalmente voltada à religião e tradição)
    perfil_carmen = {
        "psicologico": {"extroversao": 0.2, "abertura_experiencias": 0.2, "romantismo_afeto": 0.8, "ritmo_vida": 0.2, "logica_vs_emocao": 0.2, "resolucao_conflitos": 0.2, "competitividade_cooperacao": 0.2},
        "valores": {"ambicao_carreira": 0.2, "conservadorismo": 1.0, "espectro_politico": 0.9, "gestao_financeira": 0.2, "religiosidade": 1.0, "gosto_festas": 0.0},
        "interesses": {"animes": 0.0, "filmes": 0.2, "series": 0.2, "livros_ficcao": 0.1, "videogames": 0.0, "jogos_tabuleiro": 0.1, "tecnologia": 0.1, "academia": 0.0, "esportes": 0.0, "futebol": 0.0, "dancas": 0.1, "musica": 0.5, "tocar_instrumentos": 0.0, "fotografia": 0.1, "culinaria": 0.8, "idiomas": 0.1, "celebridades": 0.8, "historia": 0.2, "geografia": 0.2, "geopolitica": 0.1, "astronomia": 0.0}
    }

    print("Gerando e salvando vetores de 34 dimensões...")
    # Salvando no banco (A função salvar_perfil_usuario vai transformar os 34 valores em uma única lista)
    vetor_rafa = salvar_perfil_usuario("user_rafaell", "Rafaell", perfil_rafaell)
    salvar_perfil_usuario("user_maria", "Maria", perfil_maria)
    salvar_perfil_usuario("user_carmen", "Carmen", perfil_carmen)

    print("\nCalculando o Match perfeito para o Rafaell...")
    # Buscando proximidade vetorial
    melhores_matches = buscar_melhor_match("user_rafaell", vetor_rafa, quantidade=1)
    
    print("\n--- RESULTADO ---")
    for match in melhores_matches:
        print(f"Você deu match com {match['nome']}! Afinidade: {match['afinidade']}")
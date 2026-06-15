# src/services/chroma_service.py
import chromadb
import json
import logging
from datetime import datetime
from pathlib import Path
from src.services.interfaces import IMatchRepository

logger = logging.getLogger(__name__)

class ChromaMatchRepository(IMatchRepository):
    # Constantes do domínio encapsuladas na classe
    VALOR_NEUTRO = 0.5
    MINIMO_DIMENSOES_COMPARADAS = 3

    def __init__(self, path="./banco_vetorial"):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.db_path = str(self.base_dir / "banco_vetorial")
        self._colecao_usuarios = None

    def _obter_colecao(self):
        """Garante a inicialização Lazy/Singleton da coleção do ChromaDB"""
        if self._colecao_usuarios is None:
            chroma_client = chromadb.PersistentClient(path=self.db_path)
            self._colecao_usuarios = chroma_client.get_or_create_collection(
                name="perfis_matchai",
                metadata={"hnsw:space": "cosine"},
            )
        return self._colecao_usuarios

    def _achatar_dados_vetoriais(self, dados_extraidos_ia: dict) -> list:
        psicologico = dados_extraidos_ia.get("psicologico", {})
        valores = dados_extraidos_ia.get("valores", {})
        interesses = dados_extraidos_ia.get("interesses", {})

        return (
            list(psicologico.values()) +
            list(valores.values()) +
            list(interesses.values())
        )

    def _calcular_afinidade_mascarada(self, vetor_usuario: list, vetor_candidato: list) -> dict | None:
        pares_validos = []

        for valor_usuario, valor_candidato in zip(vetor_usuario, vetor_candidato):
            valor_usuario = round(float(valor_usuario), 2)
            valor_candidato = round(float(valor_candidato), 2)

            if valor_usuario == self.VALOR_NEUTRO or valor_candidato == self.VALOR_NEUTRO:
                continue

            pares_validos.append((valor_usuario, valor_candidato))

        if len(pares_validos) < self.MINIMO_DIMENSOES_COMPARADAS:
            return None

        diferencas = [
            abs(val_u - val_c)
            for val_u, val_c in pares_validos
        ]
        distancia_media = round(sum(diferencas) / len(diferencas), 4)
        afinidade = round((1 - distancia_media) * 100, 1)

        return {
            "afinidade": afinidade,
            "distancia_matematica": distancia_media,
            "dimensoes_comparadas": len(pares_validos),
        }

    def salvar_perfil_usuario(self, id_usuario: str, nome: str, dados_extraidos_ia: dict) -> list:
        vetor_usuario = self._achatar_dados_vetoriais(dados_extraidos_ia)
        colecao = self._obter_colecao()
        
        colecao.upsert(
            ids=[id_usuario],
            embeddings=[vetor_usuario],
            metadatas=[{"nome": nome}],
            documents=[f"Perfil de {nome}"],
        )

        logger.info(f"Perfil de {nome} salvo com sucesso! Tamanho do vetor: {len(vetor_usuario)} dimensões.")
        return vetor_usuario

    def buscar_melhor_match(self, id_usuario_buscando: str, vetor_do_usuario: list, quantidade: int = 1) -> list:
        colecao = self._obter_colecao()
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

            afinidade_calculada = self._calcular_afinidade_mascarada(
                vetor_do_usuario,
                embeddings_encontrados[i],
            )

            if afinidade_calculada is None:
                continue

            metadados = metadados_encontrados[i] if i < len(metadados_encontrados) else {}

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

    def popular_banco_mock(self):
        """Mantém a carga inicial de dados de teste de forma limpa"""
        colecao = self._obter_colecao()
        resultados = colecao.get()
        ids_existentes = set(resultados.get("ids", []))

        # ... (Mantém as definições estruturadas de perfil_maria e perfil_carmen que você criou)
        perfil_maria = { "psicologico": {"extroversao": 0.6, "abertura_experiencias": 0.6, "romantismo_afeto": 0.5, "ritmo_vida": 0.6, "logica_vs_emocao": 0.7, "resolucao_conflitos": 0.5, "competitividade_cooperacao": 0.5}, "valores": {"ambicao_carreira": 0.6, "conservadorismo": 0.4, "espectro_politico": 0.5, "gestao_financeira": 0.6, "religiosidade": 0.4, "gosto_festas": 0.6}, "interesses": {"animes": 0.9, "filmes": 0.6, "series": 0.7, "livros_ficcao": 0.8, "videogames": 0.7, "jogos_tabuleiro": 0.4, "tecnologia": 0.6, "academia": 0.8, "esportes": 0.8, "futebol": 0.9, "dancas": 0.3, "musica": 0.6, "tocar_instrumentos": 0.2, "fotografia": 0.4, "culinaria": 0.6, "idiomas": 0.6, "celebridades": 0.2, "historia": 0.5, "geografia": 0.4, "geopolitica": 0.5, "astronomia": 0.5} }
        perfil_carmen = { "psicologico": {"extroversao": 0.2, "abertura_experiencias": 0.2, "romantismo_afeto": 0.8, "ritmo_vida": 0.2, "logica_vs_emocao": 0.2, "resolucao_conflitos": 0.2, "competitividade_cooperacao": 0.2}, "valores": {"ambicao_carreira": 0.2, "conservadorismo": 1.0, "espectro_politico": 0.9, "gestao_financeira": 0.2, "religiosidade": 1.0, "gosto_festas": 0.0}, "interesses": {"animes": 0.0, "filmes": 0.2, "series": 0.2, "livros_ficcao": 0.1, "videogames": 0.0, "jogos_tabuleiro": 0.1, "tecnologia": 0.1, "academia": 0.0, "esportes": 0.0, "futebol": 0.0, "dancas": 0.1, "musica": 0.5, "tocar_instrumentos": 0.0, "fotografia": 0.1, "culinaria": 0.8, "idiomas": 0.1, "celebridades": 0.8, "historia": 0.2, "geografia": 0.2, "geopolitica": 0.1, "astronomia": 0.0} }

        perfis_mock = [
            ("user_maria", "Maria", perfil_maria),
            ("user_carmen", "Carmen", perfil_carmen),
        ]
        
        for id_usuario, nome, perfil in perfis_mock:
            if id_usuario not in ids_existentes:
                print(f"Populando banco com perfil de teste: {nome}...")
                self.salvar_perfil_usuario(id_usuario, nome, perfil)
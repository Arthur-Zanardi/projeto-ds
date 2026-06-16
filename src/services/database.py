"""Camada vetorial sobre PostgreSQL + pgvector.

Substitui o ChromaDB: os embeddings ficam na tabela `perfis_vetoriais`
(coluna `vector`), a busca usa distância de cosseno do pgvector e, sobre os
candidatos retornados, aplica-se a MESMA lógica de afinidade mascarada de
antes (ignora dimensões neutras 0.5). O esquema é criado via Alembic.
"""
import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db_models import PerfilVetorial
from src.schema.schema_vetores import (
    VetorInteresses,
    VetorPsicologico,
    VetorValores,
)
from src.services.db import session_scope
from src.services.user_context import normalizar_email_usuario

logger = logging.getLogger(__name__)

VALOR_NEUTRO = 0.5
MINIMO_DIMENSOES_COMPARADAS = 3


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

    diferencas = [abs(u - c) for u, c in pares_validos]
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
        proximas.append(
            {
                "grupo": grupo,
                "campo": campo,
                "rotulo": campo.replace("_", " ").title(),
                "diferenca": diferenca,
                "valor_usuario": valor_usuario,
                "valor_candidato": valor_candidato,
                "tem_sinal": tem_sinal,
            }
        )
    proximas.sort(key=lambda item: (not item["tem_sinal"], item["diferenca"], item["campo"]))
    return proximas[:quantidade]


# --------------------------------------------------------------------------
# Armazenamento / busca vetorial (pgvector)
# --------------------------------------------------------------------------
def _upsert_embedding(id_usuario: str, nome: str, vetor_usuario: list[float]):
    with session_scope() as s:
        stmt = (
            pg_insert(PerfilVetorial)
            .values(usuario=id_usuario, nome=nome, embedding=vetor_usuario)
            .on_conflict_do_update(
                index_elements=["usuario"],
                set_={"nome": nome, "embedding": vetor_usuario},
            )
        )
        s.execute(stmt)


def salvar_perfil_usuario(id_usuario: str, nome: str, dados_extraidos_ia: dict):
    """Achata o JSON da IA em floats e salva o embedding no pgvector."""
    id_usuario = normalizar_email_usuario(id_usuario)
    vetor_usuario = achatar_dados_vetoriais(dados_extraidos_ia)
    _upsert_embedding(id_usuario, nome, vetor_usuario)
    logger.info(
        "Perfil de %s salvo! Tamanho do vetor: %d dimensoes.", nome, len(vetor_usuario)
    )
    return vetor_usuario


def salvar_perfil_vetorial(id_usuario: str, nome: str, vetor_dict: dict):
    vetor_usuario = achatar_dados_vetoriais(vetor_dict)
    _upsert_embedding(id_usuario, nome, vetor_usuario)
    return vetor_usuario


def obter_vetor_usuario(id_usuario: str):
    with session_scope() as s:
        embedding = s.execute(
            select(PerfilVetorial.embedding).where(PerfilVetorial.usuario == id_usuario)
        ).scalar_one_or_none()
    if embedding is None:
        return None
    vetor = [float(valor) for valor in embedding]
    return vetor or None


def buscar_melhor_match(
    id_usuario_buscando: str,
    vetor_do_usuario: list,
    quantidade: int = 1,
    ids_ignorados: set[str] | None = None,
    incluir_vetor: bool = False,
):
    """Busca candidatos por distância de cosseno e re-rankeia com a
    afinidade mascarada (ignorando dimensões neutras 0.5)."""
    id_usuario_buscando = normalizar_email_usuario(id_usuario_buscando)
    limite = max(quantidade * 8, quantidade + 4)
    ids_para_ignorar = {id_usuario_buscando, *(ids_ignorados or set())}

    with session_scope() as s:
        distancia = PerfilVetorial.embedding.cosine_distance(vetor_do_usuario)
        linhas = s.execute(
            select(
                PerfilVetorial.usuario,
                PerfilVetorial.nome,
                PerfilVetorial.embedding,
            )
            .order_by(distancia.asc())
            .limit(limite)
        ).all()

    matches_reais = []
    for linha in linhas:
        if linha.usuario in ids_para_ignorar:
            continue
        vetor_candidato = [float(valor) for valor in linha.embedding]
        afinidade_calculada = calcular_afinidade_mascarada(vetor_do_usuario, vetor_candidato)
        if afinidade_calculada is None:
            continue
        match = {
            "id": linha.usuario,
            "nome": linha.nome or "Desconhecido",
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

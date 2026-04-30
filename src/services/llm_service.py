from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from src.schema.schema_vetores import default_profile_vectors, normalize_profile_vectors


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _client():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY nao configurada.")
    from groq import Groq

    return Groq(api_key=GROQ_API_KEY)


def gerar_resposta_ia(
    prompt_usuario: str,
    historico: list[dict[str, str]] | None = None,
) -> str:
    try:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Voce e a IA de onboarding do MatchAI. Converse de forma acolhedora, "
                    "curiosa e objetiva para entender gostos, valores, rotina, visao de "
                    "mundo e estilo de relacionamento do usuario. Faca no maximo uma "
                    "pergunta por resposta e responda em ate 3 linhas."
                ),
            }
        ]

        for item in (historico or [])[-10:]:
            role = "assistant" if item.get("remetente") == "ia" else "user"
            messages.append({"role": role, "content": item.get("mensagem", "")})

        messages.append({"role": "user", "content": prompt_usuario})

        completion = _client().chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=320,
        )
        return completion.choices[0].message.content
    except Exception as exc:
        return (
            "Quero te conhecer melhor. Me conta um pouco sobre sua rotina, seus "
            f"interesses e o tipo de conexao que voce procura. ({exc})"
        )


def extrair_vetores_da_conversa(historico_conversa: str) -> dict[str, dict[str, float]]:
    if not historico_conversa.strip():
        return default_profile_vectors()

    prompt_sistema = """
Voce e um especialista em analise comportamental para um aplicativo de relacionamentos.
Leia a conversa do usuario e extraia um perfil vetorial JSON.

Regras:
- Use apenas evidencias ditas pelo usuario.
- Se nao houver indicios claros, mantenha 0.5.
- Todos os valores devem ficar entre 0.0 e 1.0.
- Retorne apenas JSON valido com esta estrutura:
{
  "psicologico": {
    "extroversao": 0.5,
    "abertura_experiencias": 0.5,
    "romantismo_afeto": 0.5,
    "ritmo_vida": 0.5,
    "logica_vs_emocao": 0.5,
    "resolucao_conflitos": 0.5,
    "competitividade_cooperacao": 0.5
  },
  "valores": {
    "ambicao_carreira": 0.5,
    "conservadorismo": 0.5,
    "espectro_politico": 0.5,
    "gestao_financeira": 0.5,
    "religiosidade": 0.5,
    "gosto_festas": 0.5
  },
  "interesses": {
    "animes": 0.5,
    "filmes": 0.5,
    "series": 0.5,
    "livros_ficcao": 0.5,
    "videogames": 0.5,
    "jogos_tabuleiro": 0.5,
    "tecnologia": 0.5,
    "academia": 0.5,
    "esportes": 0.5,
    "futebol": 0.5,
    "dancas": 0.5,
    "musica": 0.5,
    "tocar_instrumentos": 0.5,
    "fotografia": 0.5,
    "culinaria": 0.5,
    "idiomas": 0.5,
    "celebridades": 0.5,
    "historia": 0.5,
    "geografia": 0.5,
    "geopolitica": 0.5,
    "astronomia": 0.5
  }
}
"""

    try:
        completion = _client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {
                    "role": "user",
                    "content": (
                        "Analise a conversa abaixo e gere o JSON de perfil:\n\n"
                        f"{historico_conversa}"
                    ),
                },
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        texto_json = completion.choices[0].message.content
        return normalize_profile_vectors(json.loads(texto_json))
    except Exception as exc:
        print(f"Erro ao extrair vetores: {exc}")
        return default_profile_vectors()


def gerar_sugestao_assunto_ia(
    perfil_usuario: dict[str, Any],
    perfil_match: dict[str, Any],
    nome_match: str,
) -> str:
    prompt = (
        "Crie uma unica sugestao curta de assunto inicial para uma conversa de match. "
        "Use os perfis vetoriais cruzados, evite parecer robotico e escreva em portugues.\n"
        f"Nome do match: {nome_match}\n"
        f"Perfil usuario: {json.dumps(normalize_profile_vectors(perfil_usuario), ensure_ascii=False)}\n"
        f"Perfil match: {json.dumps(normalize_profile_vectors(perfil_match), ensure_ascii=False)}"
    )
    try:
        completion = _client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Voce ajuda a iniciar conversas naturais em apps de namoro.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=120,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return ""

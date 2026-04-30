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
        raise RuntimeError("GROQ_API_KEY não configurada.")
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
                    "Você é a IA de onboarding do MatchAI. Converse de forma acolhedora, "
                    "curiosa e objetiva para entender gostos, valores, rotina, atração "
                    "física, visão de mundo e estilo de relacionamento do usuário. Faça no máximo uma "
                    "pergunta por resposta e responda em até 3 linhas."
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
            f"interesses e o tipo de conexão que você procura. ({exc})"
        )


def extrair_vetores_da_conversa(historico_conversa: str) -> dict[str, dict[str, float]]:
    if not historico_conversa.strip():
        return default_profile_vectors()

    schema_example = json.dumps(default_profile_vectors(), ensure_ascii=False, indent=2)
    prompt_sistema = f"""
Você é um especialista em análise comportamental para um aplicativo de relacionamentos.
Leia a conversa do usuário e extraia um JSON de perfil.

Regras:
- Use apenas evidências ditas pelo usuário.
- Se não houver indícios claros, mantenha 0.5.
- Todos os valores devem ficar entre 0.0 e 1.0.
- O grupo "fisico" representa características reais do usuário e NÃO deve ser inferido pela conversa; mantenha 0.5.
- O grupo "atracao" representa preferências físicas que o usuário disse gostar.
- Retorne apenas JSON válido com esta estrutura:
{schema_example}
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
        print(f"Erro ao extrair perfil: {exc}")
        return default_profile_vectors()


def gerar_sugestao_assunto_ia(
    perfil_usuario: dict[str, Any],
    perfil_match: dict[str, Any],
    nome_match: str,
) -> str:
    prompt = (
        "Crie uma única sugestão curta de assunto inicial para uma conversa de match. "
        "Use os perfis cruzados, evite parecer robótico e escreva em português.\n"
        f"Nome do match: {nome_match}\n"
        f"Perfil usuário: {json.dumps(normalize_profile_vectors(perfil_usuario), ensure_ascii=False)}\n"
        f"Perfil match: {json.dumps(normalize_profile_vectors(perfil_match), ensure_ascii=False)}"
    )
    try:
        completion = _client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Você ajuda a iniciar conversas naturais em apps de namoro.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=120,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return ""

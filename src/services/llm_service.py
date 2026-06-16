"""Integração com o LLM (Groq) para conversa e extração de vetores de perfil."""
import json
import logging

from src.config import settings
from src.schema.schema_vetores import PerfilUsuarioVetorizado

logger = logging.getLogger(__name__)

CHAVE_GROQ = settings.groq_api_key

client = None


class LLMServiceError(Exception):
    pass


def obter_cliente_groq():
    global client

    if client is None:
        from groq import Groq

        client = Groq(api_key=CHAVE_GROQ)

    return client


def _system_prompt_assistente(nome_usuario: str | None = None) -> str:
    base = (
        "Você é o assistente do MatchAI, um aplicativo de relacionamentos. "
        "Seu papel é conversar de forma acolhedora para ajudar a pessoa a "
        "montar o próprio perfil e descobrir conexões reais por afinidade. "
        "Faça perguntas leves sobre gostos, valores e personalidade. "
        "Responda em no máximo 2 linhas."
    )
    if nome_usuario:
        base += f" Quando fizer sentido, você pode se dirigir à pessoa como {nome_usuario}."
    return base


def gerar_resposta_ia(prompt_usuario: str, nome_usuario: str | None = None) -> str:
    try:
        completion = obter_cliente_groq().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": _system_prompt_assistente(nome_usuario),
                },
                {
                    "role": "user",
                    "content": prompt_usuario,
                },
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        return completion.choices[0].message.content

    except Exception as e:
        logger.exception("Erro na integração com a Groq.")
        raise LLMServiceError(f"Erro na integracao com Groq: {e}") from e


def extrair_vetores_da_conversa(historico_conversa: str) -> dict:
    prompt_sistema = """
    Você é um especialista em psicologia e análise comportamental para um aplicativo de relacionamentos.
    Sua missão é ler a conversa do usuário e extrair um perfil vetorial em formato JSON.

    Regras de Avaliação (Escala 0.00 a 1.00):
    - Avalie cada característica com base EXCLUSIVAMENTE no que foi dito no texto.
    - Se o usuário NÃO deu indícios claros sobre um tema, mantenha o valor padrão de 0.50.
    - 0.0 representa aversão, falta absoluta ou o extremo oposto da característica.
    - 1.0 representa paixão, presença absoluta ou dedicação total à característica.
    - Use valores com até duas casas decimais, como 0.46, 0.64, 0.82 ou 0.96.
    - Você pode aumentar ou diminuir os valores em centésimos conforme a força da evidência.
    - Não arredonde tudo para 0.0, 0.5 ou 1.0.
    - 0.50 deve significar apenas ausência de evidência clara, neutralidade ou dado desconhecido.

    Você deve retornar APENAS um objeto JSON válido, com a exata estrutura abaixo, substituindo os valores de 0.50 apenas quando tiver evidências claras na conversa:
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
        completion = obter_cliente_groq().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {
                    "role": "user",
                    "content": f"Analise o seguinte trecho de conversa do usuário e gere o JSON de perfil:\n\n'{historico_conversa}'",
                },
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        texto_json = completion.choices[0].message.content
        dados_extraidos = json.loads(texto_json)
        perfil_validado = PerfilUsuarioVetorizado.model_validate(dados_extraidos)
        return perfil_validado.model_dump()

    except Exception as e:
        logger.exception("Erro ao extrair vetores da conversa.")
        raise LLMServiceError(f"Erro ao extrair vetores: {e}") from e

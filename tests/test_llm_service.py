import json

import pytest

from src.services import llm_service


class CompletionFake:
    def __init__(self, content):
        self.choices = [
            type(
                "Choice",
                (),
                {"message": type("Message", (), {"content": content})()},
            )()
        ]


class ClienteGroqFake:
    def __init__(self, content):
        self.chat = type(
            "Chat",
            (),
            {
                "completions": type(
                    "Completions",
                    (),
                    {"create": lambda _, **kwargs: CompletionFake(content)},
                )()
            },
        )()


def test_extrair_vetores_normaliza_resposta_da_ia(monkeypatch):
    resposta_json = json.dumps({
        "psicologico": {"extroversao": 0.644},
        "valores": {"religiosidade": 0.963},
        "interesses": {"musica": 0.5},
    })
    monkeypatch.setattr(
        llm_service,
        "obter_cliente_groq",
        lambda: ClienteGroqFake(resposta_json),
    )

    resultado = llm_service.extrair_vetores_da_conversa("gosto de musica")

    assert resultado["psicologico"]["extroversao"] == 0.64
    assert resultado["valores"]["religiosidade"] == 0.96
    assert resultado["interesses"]["musica"] == 0.5


def test_extrair_vetores_rejeita_resposta_invalida_da_ia(monkeypatch):
    resposta_json = json.dumps({
        "psicologico": {"extroversao": 1.5},
        "valores": {},
        "interesses": {},
    })
    monkeypatch.setattr(
        llm_service,
        "obter_cliente_groq",
        lambda: ClienteGroqFake(resposta_json),
    )

    with pytest.raises(llm_service.LLMServiceError):
        llm_service.extrair_vetores_da_conversa("texto")

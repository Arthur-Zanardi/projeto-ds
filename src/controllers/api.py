from fastapi import FastAPI
from pydantic import BaseModel

import sys
from pathlib import Path

root = Path('/src/services').resolve()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from llm_service import gerar_resposta_ia, extrair_vetores_da_conversa


app = FastAPI(
    title="MatchAI API",
    description="Backend para o aplicativo de relacionamento",
    version="0.1.0"
)

# Definimos como deve ser o "corpo" da requisição JSON que a API vai receber
class MensagemUsuario(BaseModel):
    texto: str

@app.get("/")
def read_root():
    return {"mensagem": "API do MatchAI está rodando perfeitamente!"}

# Criamos uma rota POST para enviar os dados para a IA
@app.post("/chat")
def conversar_com_ia(mensagem: MensagemUsuario):
    # Aqui chamamos a sua função passando o texto que chegou na requisição
    resposta = gerar_resposta_ia(mensagem.texto)
    
    # E devolvemos a resposta no formato JSON
    return {"resposta": resposta}

@app.post("/analisar_perfil")
def analisar_perfil(mensagem: MensagemUsuario):
    # Passamos o texto para a nossa nova função extratora
    vetores_json = extrair_vetores_da_conversa(mensagem.texto)
    
    return {
        "texto_analisado": mensagem.texto,
        "vetores_calculados": vetores_json
    }
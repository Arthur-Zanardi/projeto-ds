from fastapi import FastAPI
from pydantic import BaseModel
from src.services.llm_service import gerar_resposta_ia

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
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
CHAVE_GROQ = os.getenv("GROQ_API_KEY")

client = Groq(api_key=CHAVE_GROQ)


nome = "Meu nome é Rafaell Saraiva"
idade = "Minha idade é 18 anos"

traco1 = "Sou extrovertido"
traco2 = "Sou empático"
traco3 = "Sou sapeca"

tracos = f"Meus traços de personalidade são: {traco1}, {traco2}, e {traco3}."

pessoa1 = "Pessoa 1: Letícia, 18, Gotica Rabuda, Alternativa, Satanista."
pessoa2 = "Pessoa 2: Maria do Carmo, 24, Mórmom, Conservadora, Sádica."
existe = True
if (existe):
    cabecalho = "Essas são caracteristicas minhas. Pode se referir a mim pelo nome mas não precisa mencionar ela sempre."
else:
    cabecalho = ""

def gerar_resposta_ia(prompt_usuario):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": f"Você me auxilia à encontrar meu amor da minha vida. {cabecalho} {nome}.{idade}.{tracos}, {pessoa1}, {pessoa2}"
                },
                {
                    "role": "user",
                    "content": prompt_usuario
                }
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        
        return completion.choices[0].message.content

    except Exception as e:
        return f"Erro na integração com Groq: {e}"
# Teste do MVP
"""
if __name__ == "__main__":

    print("--- Teste de Conexão IA (GROQ CLOUD) ---")
    pergunta = "Como posso ajudar a juntar duas pessoas que estão se afastando?"
    print(f"Pergunta: {pergunta}")
    
    resposta = gerar_resposta_ia(pergunta)
    print(f"\nResposta da IA:\n{resposta}")
"""
while(True):
    pergunta = input("Digite sua pergunta para a IA (ou 'sair' para encerrar): ")
    if pergunta.lower() == "sair":
        print("Encerrando o programa. Até mais!")
        break
    
    resposta = gerar_resposta_ia(pergunta)
    print(f"\nResposta da IA:\n{resposta}\n")
import os
from groq import Groq
from dotenv import load_dotenv
import json



load_dotenv()
CHAVE_GROQ = os.getenv("GROQ_API_KEY")

client = Groq(api_key=CHAVE_GROQ)


nome = "Meu nome é Rafaell Saraiva"
idade = "Minha idade é 18 anos"

traco1 = "Sou extrovertido"
traco2 = "Sou empático"
traco3 = "Sou sapeca"

tracos = f"Meus traços de personalidade são: {traco1}, {traco2}, e {traco3}."

pessoa1 = "Pessoa 1: Letícia, 19, Estudante de Design Gráfico, Fotografia analógica e garimpo em sebos, Criativa, Espontânea, Cabelo comprido, Alta."
pessoa2 = "Pessoa 2: Maria do Carmo, 20, Estudante de Letras, Prática de Yoga e maratonar documentários de crimes reais, Analítica, Paciente, Cabelo curto e ondulado, baixa."
existe = False
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
                    "content": f"Você me auxilia à encontrar meu amor da minha vida. {cabecalho} {nome}.{idade}. Responda em 2 linhas"
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
    

#função para pegar vetores

def extrair_vetores_da_conversa(historico_conversa: str) -> dict:
    prompt_sistema = """
    Você é um especialista em psicologia e análise comportamental para um aplicativo de relacionamentos.
    Sua missão é ler a conversa do usuário e extrair um perfil vetorial em formato JSON.
    
    Regras de Avaliação (Escala 0.0 a 1.0):
    - Avalie cada característica com base EXCLUSIVAMENTE no que foi dito no texto.
    - Se o usuário NÃO deu indícios claros sobre um tema, mantenha o valor padrão de 0.5.
    - 0.0 representa aversão, falta absoluta ou o extremo oposto da característica.
    - 1.0 representa paixão, presença absoluta ou dedicação total à característica.

    Você deve retornar APENAS um objeto JSON válido, com a exata estrutura abaixo, substituindo os valores de 0.5 apenas quando tiver evidências claras na conversa:
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
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {
                    "role": "user", 
                    "content": f"Analise o seguinte trecho de conversa do usuário e gere o JSON de perfil:\n\n'{historico_conversa}'"
                }
            ],
            temperature=0.0, # Mantemos em 0 para a IA ser analítica e não inventar dados
            response_format={"type": "json_object"} # Força a API da Groq a validar que a saída é um JSON
        )
        
        texto_json = completion.choices[0].message.content
        dados_extraidos = json.loads(texto_json)
        return dados_extraidos

    except Exception as e:
        print(f"Erro ao extrair vetores: {e}")
        return {}
    

# Teste do MVP
"""
if __name__ == "__main__":

    print("--- Teste de Conexão IA (GROQ CLOUD) ---")
    pergunta = "Como posso ajudar a juntar duas pessoas que estão se afastando?"
    print(f"Pergunta: {pergunta}")
    
    resposta = gerar_resposta_ia(pergunta)
    print(f"\nResposta da IA:\n{resposta}")
"""
# while(True):
#     pergunta = input("Digite sua pergunta para a IA (ou 'sair' para encerrar): ")
#     if pergunta.lower() == "sair":
#         print("Encerrando o programa. Até mais!")
#         break
    
#     resposta = gerar_resposta_ia(pergunta)
#     print(f"\nResposta da IA:\n{resposta}\n")

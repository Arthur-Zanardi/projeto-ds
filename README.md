  # MatchAI - Conexões Profundas via IA 🤖❤️

O **MatchAI** é um aplicativo de relacionamento focado na Geração Z (18-26 anos) que utiliza Inteligência Artificial (LLMs) para gerar conexões baseadas em afinidade real, valores e opiniões sinceras, indo além da superficialidade estética.

## 🚀 Funcionalidades Principais
- **Perfil dinâmico:** Chat interativo para criação de perfil.
- **Extração Semântica:** Uso de LLM para transformar conversas em dados estruturados (JSON).
- **Match por Similaridade:** Algoritmo baseado em Embeddings e Distância entre Vetores.
- **Interface Flet:** UI moderna construída inteiramente em Python.

## 🛠️ Tecnologias e Bibliotecas
- **Linguagem:** [Python 3.10+](https://www.python.org/)
- **Interface:** [Flet](https://flet.dev/)
- **Cérebro (LLM):** [Groq](https://console.groq.com/home)
- **Banco de Dados Vetorial:** [ChromaDB](https://www.trychroma.com/)

## 📦 Como rodar o projeto

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/match-ai.git](https://github.com/seu-usuario/match-ai.git)
   cd match-ai```
   
2. **Crie um ambiente virtual:**

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

3. **Instale as dependências:**

```bash
pip install -e .
```

4. **Configure as chaves de API:**

Crie um arquivo .env na raiz do projeto.

Adicione sua chave: GEMINI_API_KEY={sua_chave_aqui}

5. **Execute o app:**

```bash
flet run main.py
```

## 🏗️ Arquitetura
O projeto segue o padrão MVC (Model-View-Controller) com uma camada adicional de Services para isolar a lógica da IA.

```plaintext
match-ai/
├── main.py              # Ponto de entrada
├── assets/              # Imagens, fontes e ícones
├── src/
│   ├── models/          # (M) Classes de dados (User, Match)
│   │
│   ├── services/        # O "Cérebro" (llm_service.py, vector_service.py)
│   │
│   ├── views/           # (V) Telas e Componentes
│   │   ├── login_view.py
│   │   ├── chat_view.py
│   │   └── components/  # Botões, cards e inputs personalizados
│   │
│   └── controllers/     # (C) Lógica que conecta a View ao Service
│       └── chat_controller.py
└── .env                 # API Keys
```

## 🤍 Como contribuir
Acesse [CONTRIBUTING](https://github.com/Arthur-Zanardi/projeto-ds/blob/main/CONTRIBUTING.md)

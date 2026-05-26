# Manual do Desenvolvedor - MatchAI 🤖❤️

## 1. Visão Geral do Projeto
O MatchAI é um aplicativo de relacionamento inovador que utiliza Inteligência Artificial para interagir com o usuário, extrair um perfil vetorial com base na conversação e calcular a compatibilidade matemática com uma base de perfis candidatos (nesta etapa de desenvolvimento, utilizando perfis pré-estabelecidos/mocks para validação do algoritmo).

A arquitetura do projeto é construída inteiramente em Python, adotando o padrão MVC com uma camada de serviços isolada. A interface gráfica (Frontend) é desenvolvida com o framework Flet, enquanto a API (Backend) é orquestrada via FastAPI. O sistema utiliza SQLite para persistência relacional (histórico e logs) e ChromaDB como banco de dados vetorial para as operações matemáticas de match semântico, alimentado pelas respostas da IA via Groq/LLM.

## 2. Estrutura de Pastas
O repositório está organizado para separar claramente a interface, as rotas de API, a lógica de negócio e os modelos de dados, baseando-se na imagem da árvore do repositório.

```markdown
PROJETO-DS/
├── assets/                   # Recursos estáticos (fonts, icons)
├── banco_vetorial/           # Diretório de armazenamento local do ChromaDB
├── src/                      # Código-fonte principal da aplicação
│   ├── controllers/          # Rotas da API e orquestração (FastAPI)
│   │   ├── api.py            # Definição dos endpoints principais
│   │   └── match_controller.py # Lógica de controle focada no algoritmo de match
│   ├── models/               # Modelos de dados e entidades
│   │   └── user.py           # Definição do usuário
│   ├── schema/               # Validação de dados (Pydantic)
│   │   └── schema_vetores.py # Contratos para entrada/saída dos vetores
│   ├── services/             # Regras de negócio, integrações externas e bancos
│   │   ├── api_client.py     # Cliente HTTP interno
│   │   ├── database.py       # Interação com o banco vetorial (ChromaDB)
│   │   ├── embedding_service.py # Geração e manipulação de embeddings
│   │   ├── llm_conversation.py  # Lógica de chat contínuo
│   │   ├── llm_service.py    # Integração direta com a API da IA (Groq)
│   │   └── sqlite_db.py      # I/O do banco relacional
│   ├── utils/                # Utilitários e funções de apoio
│   │   └── navigation.py     # Gerenciamento de rotas visuais no Flet
│   └── views/                # Telas e interface gráfica (Flet)
│       ├── chat_view.py      # Tela de conversação e botão de match
│       ├── login_view.py     # Tela de autenticação
│       └── match_view.py     # Tela de exibição de resultados
├── api.py                    # Script raiz para execução do servidor FastAPI
├── banco_relacional.db       # Arquivo de banco de dados SQLite local
├── main.py                   # Ponto de entrada da interface gráfica Flet
├── pyproject.toml            # Configurações do projeto e ferramentas (ex: pytest)
└── requirements.txt          # Dependências do projeto (FastAPI, Flet, ChromaDB, etc.)

```

## 3. Arquitetura e Padrões de Código

O projeto impõe uma separação estrita de responsabilidades:

* **Views:** Arquivos em `src/views/` são estritamente visuais e não contêm regras de negócio.
* **Controllers:** Arquivos em `src/controllers/` recebem as requisições HTTP, repassam para os services e formatam a resposta.
* **Services:** O core do sistema (`src/services/`) concentra a manipulação dos bancos (SQLite/ChromaDB), integração com IA, geração de embeddings e cálculos matemáticos de match.
* **Schemas:** Os modelos Pydantic em `src/schema/` atuam como validadores de entrada e saída, garantindo a estrutura correta dos dados.

### Tratamento de Erros e Controle de Estado

* **Entradas Malformadas:** Os schemas interceptam dados inválidos. As anomalias são logadas no banco e a requisição é barrada.
* **Falhas Externas:** Quedas de comunicação com a Groq são capturadas via blocos `try/except` em `llm_service.py`.
* **Feedback Visual:** Qualquer erro na API retorna mensagens amigáveis no chat (Flet), impedindo o travamento da interface. Todos os eventos críticos são gravados na tabela `logs_api` do SQLite.

## 4. Bancos de Dados

### SQLite (Relacional)

O arquivo `banco_relacional.db` gerencia o histórico estruturado e a auditoria do sistema através das seguintes tabelas principais:

* `historico_chat`: Salva o log sequencial das mensagens enviadas pelo usuário e geradas pela IA.
* `vetores_salvos`: Mantém o histórico dos perfis vetoriais extraídos.
* `logs_api`: Registra chamadas aos endpoints e eventos de sistema.

### ChromaDB (Vetorial)

Persistido na pasta `banco_vetorial/`. O banco vetorial não guarda texto bruto, mas sim representações dimensionais (**embeddings**) dos perfis, permitindo consultas matemáticas de similaridade entre usuários e perfis mockados.

## 5. Como Configurar o Ambiente Local

**Pré-requisitos:**

* Python 3.10+
* Chave válida da API da Groq

**Passo a passo:**

1. **Instalar dependências:**
Abra o terminal na pasta raiz do projeto:

```bash
pip install -r requirements.txt
# Ou, utilizando instalação local:
pip install -e .

```

2. **Variáveis de Ambiente:**
Crie um arquivo `.env` na raiz do projeto:

```env
GROQ_API_KEY=sua_chave_aqui

```

3. **Rodar a API (Backend):**
Execute o servidor FastAPI:

```bash
fastapi dev api.py

```

4. **Rodar a Interface Gráfica (Frontend):**
Em outro terminal:

```bash
flet run main.py

```

## 6. Fluxo Principal e Algoritmo de Match

### Fluxo de Interação

1. O usuário envia uma mensagem pela `chat_view`.
2. A mensagem é enviada ao controller (`/chat`).
3. O controller salva a entrada no SQLite.
4. O `llm_service` gera a resposta da IA.
5. O perfil vetorial é recalculado.
6. O vetor é salvo no SQLite e no ChromaDB.

### O Algoritmo de `/dar_match`

A ação de Match não chama a IA. Ela resgata o último vetor salvo no banco e o compara com os vetores da base de perfis (atualmente operando com mocks).

**Regras do cálculo:**

* Os valores vetoriais variam de `0.00` a `1.00`.
* O valor `0.50` representa neutralidade/ausência de evidência.
* Dimensões com valor `0.50` são ignoradas no cálculo.
* É necessário pelo menos **3 dimensões válidas** para calcular afinidade.

**Retorno do endpoint:**
O endpoint retorna o nome do perfil compatível, a pontuação de afinidade e a quantidade de dimensões utilizadas.

## 7. Testes Automatizados

O projeto utiliza **pytest** para validar as rotas da API, funções matemáticas do match, persistência no SQLite e validação de schemas.

As chamadas para IA são mockadas para garantir:

* Testes determinísticos
* Execução rápida
* Zero custo de rede

Para executar os testes, rode no terminal:

```bash
pytest

```

---

# Contribuindo para o MatchAI 🤝

Bem-vindo ao time! Para manter a qualidade do código e a agilidade do SCRUM, siga estas diretrizes:

## 🌿 Estratégia de Branchs

* `main`: Código estável e pronto para demonstração.
* `developer`: Branch de integração das funcionalidades da Sprint atual para cada desenvolvedor.
* `feature/nome-da-feature`: Branch para desenvolvimento de novas tarefas.

## 🏗️ Padrões de Código

* **Async/Await:** Como usamos Flet e APIs externas, todas as chamadas de rede/IA devem ser assíncronas.
* **MVC + Services:** Não coloque lógica de IA dentro das Views. Crie um Service em `src/services/` e chame-o através de um Controller.
* **Clean Code:** Tente aderir aos padrões estabelecidos neste [doc](https://docs.google.com/document/d/1VsjZOmuIE6xwqX6GkzYR8DSCWdKbUxnnjzqULNFnSAU/edit?usp=sharing) sempre que possível.

## 🚀 Processo de Pull Request

1. Garanta que seu código está formatado e sem erros.
2. Abra o PR apontando para a branch adequado.
3. Aguarde o Code Review de pelo menos um integrante.
4. Após aprovado, realize o Merge.

```

```

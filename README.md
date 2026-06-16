# MatchAI — Conexões Profundas via IA 🤖❤️

O **MatchAI** é um aplicativo de relacionamento focado na Geração Z que usa IA (LLMs)
para gerar conexões por **afinidade real** — valores, personalidade e interesses —
indo além da estética.

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Frontend | [Flet](https://flet.dev/) (web) |
| API | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| Banco relacional + vetorial | [PostgreSQL 16](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) |
| ORM / Migrações | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/) |
| Autenticação | JWT ([python-jose](https://github.com/mpdavis/python-jose)) + bcrypt |
| LLM | [Groq](https://console.groq.com/) |
| Deploy | Docker + Docker Compose |

## ⚙️ Variáveis de ambiente

Copie `.env.example` para `.env` e preencha. Obrigatórias em produção:
`DATABASE_URL`, `JWT_SECRET`, `GROQ_API_KEY`.

| Variável | Descrição |
|---|---|
| `ENV` | `dev` ou `prod` (em prod, valida obrigatórias) |
| `DATABASE_URL` | `postgresql+psycopg://user:senha@host:5432/banco` |
| `JWT_SECRET` | segredo forte (>= 32 chars) |
| `JWT_ALGORITHM` | padrão `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | padrão `1440` |
| `GROQ_API_KEY` | chave da Groq |
| `MATCHAI_API_BASE_URL` | URL da API usada pelo frontend |
| `CORS_ALLOW_ORIGINS` | origens permitidas, separadas por vírgula (ou `*`) |
| `ADMIN_EMAILS` | e-mails admin, separados por vírgula |
| `SEED_ON_STARTUP` | `true` popula perfis mock em dev |

Gere o segredo: `python -c "import secrets; print(secrets.token_urlsafe(64))"`

## 🐳 Rodando com Docker Compose (recomendado)

```bash
cp .env.example .env       # ajuste GROQ_API_KEY e JWT_SECRET
docker compose up --build
```

Sobe `db` (PostgreSQL + pgvector), `api` (aplica migrações e faz seed em dev) e `web`:
- API: http://localhost:8000 — health em `/health`, docs em `/docs`
- Frontend: http://localhost:8550

## 💻 Rodando localmente (sem Docker)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # configure DATABASE_URL etc.

# Postgres local com pgvector (ex.: container):
docker run -d --name matchai-db -p 5432:5432 \
  -e POSTGRES_USER=matchai -e POSTGRES_PASSWORD=matchai -e POSTGRES_DB=matchai \
  pgvector/pgvector:pg16

alembic upgrade head        # cria o esquema
python -m scripts.seed      # perfis mock (opcional)
uvicorn src.controllers.api:app --reload   # API
flet run main.py            # frontend (outra aba)
```

## 🗄️ Migrações e seed

```bash
alembic upgrade head                               # aplica o esquema
alembic revision --autogenerate -m "descricao"     # nova migração
python -m scripts.seed                             # perfis mock (Maria, Carmen, Lia)
python -m scripts.migrar_sqlite_para_postgres \
  --sqlite ./banco_relacional.db --chroma ./banco_vetorial   # migrar dados antigos (opcional)
```

O esquema é criado/evoluído **apenas via Alembic** — nunca em runtime.

## 🔐 Autenticação

A API usa JWT. Fluxo: `POST /auth/register` e `POST /auth/login` retornam
`access_token`. As rotas protegidas exigem `Authorization: Bearer <token>`.
Admin é definido por
`ADMIN_EMAILS` e codificado no claim `is_admin` do token.

## 🧪 Testes e qualidade

```bash
pip install ruff pytest
ruff check .          # lint
ruff format .         # formatação
pytest -q             # testes (precisam de DATABASE_URL; sem banco, são pulados)
```

Há um workflow de CI em `.github/workflows/ci.yml` que sobe Postgres+pgvector,
roda migrações, lint e `pytest`.

## 🏗️ Arquitetura

```plaintext
match-ai/
├── main.py                     # entrada do frontend Flet
├── alembic/                    # migrações (esquema + extensão vector)
├── scripts/                    # seed.py, migrar_sqlite_para_postgres.py
├── src/
│   ├── config.py               # settings (pydantic-settings)
│   ├── models/db_models.py     # modelos SQLAlchemy (+ perfis_vetoriais/pgvector)
│   ├── services/
│   │   ├── db.py               # engine, pool, sessões
│   │   ├── postgres_db.py      # camada de dados (PostgresUserRepository)
│   │   ├── database.py         # busca vetorial (pgvector) + afinidade mascarada
│   │   ├── auth.py             # JWT (get_current_user)
│   │   └── llm_service.py      # integração Groq
│   ├── controllers/api.py      # FastAPI (auth, chat, matches, perfis, /health)
│   └── views/                  # telas Flet
├── Dockerfile.api / Dockerfile.web / docker-compose.yml
└── DEPLOY.md                   # guia de deploy
```

Veja **[DEPLOY.md](DEPLOY.md)** para deploy em Render/Railway/VPS.



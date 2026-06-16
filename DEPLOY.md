# Deploy do MatchAI

Stack de produção: **FastAPI** (API) + **Flet web** (frontend) + **PostgreSQL 16 + pgvector**.
Esquema gerido por **Alembic**; autenticação via **JWT**.

## 1. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Obrigatória (prod) | Descrição |
|---|---|---|
| `ENV` | — | `dev` ou `prod` |
| `DATABASE_URL` | ✅ | `postgresql+psycopg://user:senha@host:5432/banco` |
| `JWT_SECRET` | ✅ | segredo forte (>= 32 chars) |
| `JWT_ALGORITHM` | — | padrão `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | padrão `1440` |
| `GROQ_API_KEY` | ✅ | chave da Groq |
| `MATCHAI_API_BASE_URL` | — | URL da API vista pelo frontend |
| `CORS_ALLOW_ORIGINS` | — | origens separadas por vírgula |
| `ADMIN_EMAILS` | — | e-mails admin separados por vírgula |
| `SEED_ON_STARTUP` | — | `true` popula mocks em dev |

Gere um segredo: `python -c "import secrets; print(secrets.token_urlsafe(64))"`

## 2. Local com Docker Compose

```bash
cp .env.example .env      # ajuste GROQ_API_KEY e JWT_SECRET
docker compose up --build
```

Sobe `db` (pgvector) + `api` (migra e faz seed) + `web`.
- API: http://localhost:8000  (health em `/health`, docs em `/docs`)
- Frontend: http://localhost:8550

## 3. Postgres gerenciado com pgvector

Provedores com pgvector: **Neon**, **Supabase**, **AWS RDS** (extensão `vector`),
**Render Postgres**. Crie o banco e habilite a extensão (a migration inicial roda
`CREATE EXTENSION IF NOT EXISTS vector`; em alguns provedores é preciso habilitar
pelo painel). Use a `DATABASE_URL` no formato
`postgresql+psycopg://USUARIO:SENHA@HOST:5432/BANCO?sslmode=require`.

## 4. Render / Railway / VPS

**Render / Railway**
1. Crie um Postgres gerenciado com pgvector e copie a `DATABASE_URL`.
2. Serviço da API a partir de `Dockerfile.api`. Variáveis: `ENV=prod`,
   `DATABASE_URL`, `JWT_SECRET`, `GROQ_API_KEY`, `CORS_ALLOW_ORIGINS`,
   `ADMIN_EMAILS`. O `entrypoint.sh` roda `alembic upgrade head` no start.
3. Serviço do frontend a partir de `Dockerfile.web` com
   `MATCHAI_API_BASE_URL=https://SUA-API`.
4. Rode o seed manualmente em prod, se quiser: `python -m scripts.seed`.

**VPS (Docker)**
```bash
git clone <repo> && cd <repo>
cp .env.example .env   # ENV=prod, segredos reais
docker compose -f docker-compose.yml up -d --build
```
Coloque um proxy reverso (Caddy/Nginx) com TLS na frente da API e do frontend.

## 5. Migrações e seed

```bash
alembic upgrade head           # aplica o esquema
alembic revision --autogenerate -m "mudanca"   # nova migration
python -m scripts.seed         # perfis mock (Maria, Carmen, Lia)
python -m scripts.migrar_sqlite_para_postgres --sqlite ./banco_relacional.db --chroma ./banco_vetorial
```

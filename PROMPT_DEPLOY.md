# Prompt — Preparar MatchAI para produção (Postgres + pgvector + Docker + Auth JWT)

> Cole este prompt inteiro num agente de código (Claude Code) com o repositório aberto. Ele descreve **tudo** que deve ser feito para deixar o projeto pronto para deploy. Execute em ordem; **não pule a Fase 0 (segurança)**.

---

Você é um engenheiro sênior. O projeto `MatchAI` é um app de relacionamento com **Flet** (frontend Python), **FastAPI** (backend), hoje usando **SQLite** (relacional) + **ChromaDB** (vetorial) + **Groq** (LLM). Quero deixá-lo **pronto para produção** com deploy via **Docker**, banco unificado em **PostgreSQL + pgvector**, acesso via **SQLAlchemy + Alembic**, e **autenticação JWT real** na API. Trabalhe em branch nova (`prod-hardening`), faça commits pequenos e descritivos por fase, e ao final rode os testes e me dê um resumo do que mudou.

Antes de começar: leia `main.py`, `src/controllers/api.py`, `src/services/sqlite_db.py`, `src/services/database.py`, `src/services/llm_service.py`, `src/services/user_context.py`, `src/services/api_client.py`, `src/controllers/login_controller.py` e os testes em `tests/`. Mantenha a arquitetura MVC + camada de services e a interface `IUserRepository`.

## Fase 0 — Segurança e higiene do repositório (FAZER PRIMEIRO)

1. **Remover segredos e bancos do versionamento.** Hoje estão commitados: `banco_relacional.db`, `banco_vetorial/` (chroma + .bin), `.env`, `tmp_api_8002.log`, `__pycache__/`, `.pytest_cache/`. Remova-os do índice do git com `git rm --cached` (mantendo no disco local), e garanta que o `.gitignore` cobre: `*.db`, `banco_relacional.db`, `banco_vetorial/`, `.env`, `*.log`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `dist/`, `build/`.
2. **A `GROQ_API_KEY` em `.env` foi exposta no histórico do git** — me avise no resumo final que essa chave deve ser **revogada e regenerada** no console da Groq, pois remover do git não apaga o histórico.
3. Crie um `.env.example` com todas as variáveis usadas (sem valores reais): `GROQ_API_KEY`, `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `MATCHAI_API_BASE_URL`, `CHROMA_PATH` (se aplicável), `CORS_ALLOW_ORIGINS`.
4. **Remover dados pessoais hardcoded.** Em `user_context.py`, `ADMIN_EMAILS` e `EMAIL_USUARIO_PADRAO`/`NOME_USUARIO_PADRAO` apontam para um e-mail pessoal. Mova `ADMIN_EMAILS` para variável de ambiente (`ADMIN_EMAILS` separada por vírgula). Revise o padrão perigoso em `normalizar_email_usuario`, que **retorna o e-mail admin por padrão quando nenhum e-mail é passado** — isso vira fonte de impersonação; veja Fase 3.
5. Em `llm_service.py`, **remova todo o código morto e os dados pessoais hardcoded** (`nome = "Meu nome é Rafaell Saraiva"`, `idade`, `traco1..3`, `pessoa1`, `pessoa2`, `existe`, blocos comentados de teste/`while`). Reescreva o `system prompt` de `gerar_resposta_ia` para ser genérico (assistente de relacionamentos que ajuda o usuário a montar o perfil), sem nome/idade fixos. Se nome do usuário for útil, receba como parâmetro.
6. Substitua todos os `print(...)` de diagnóstico (em `database.py`, `main.py` `route_change`, `api_client.py`) por `logging`.

## Fase 1 — Configuração centralizada

1. Crie `src/config.py` com um objeto de settings (use `pydantic-settings`) que lê do ambiente: `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM` (default `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440), `GROQ_API_KEY`, `MATCHAI_API_BASE_URL`, `CORS_ALLOW_ORIGINS`, `ADMIN_EMAILS`, `ENV` (`dev`/`prod`). Falhe rápido (erro claro) se variáveis obrigatórias faltarem em `prod`.
2. Substitua os usos espalhados de `os.getenv` por `from src.config import settings`.

## Fase 2 — Migração SQLite → PostgreSQL + pgvector (SQLAlchemy + Alembic)

1. **Dependências:** adicione ao `pyproject.toml`/`requirements.txt`: `sqlalchemy>=2.0`, `alembic`, `psycopg[binary]>=3.1`, `pgvector`, `pydantic-settings`, `python-jose[cryptography]` (JWT), `passlib[bcrypt]` (ou mantenha `bcrypt`), `uvicorn[standard]`. Remova `chromadb` quando a migração vetorial estiver concluída.
2. **Modelos SQLAlchemy** em `src/models/db_models.py` espelhando as tabelas atuais de `sqlite_db.py`: `usuarios`, `perfis_publicos`, `matches_usuario`, `conversas_match`, `mensagens_conversa`, `mensagens_match` (avalie consolidar com `mensagens_conversa`), `historico_chat`, `acoes_match`, `vetores_salvos`, `logs_api`. Use tipos nativos do Postgres: `SERIAL/IDENTITY` para PKs autoincrement, `TIMESTAMP WITH TIME ZONE` (com default no servidor) no lugar das strings de data, `JSONB` no lugar dos campos `*_json` (TEXT com JSON), `BOOLEAN` no lugar de inteiros 0/1, e `CHECK`/constraints equivalentes. Recrie todos os índices e as FKs com `ON DELETE` equivalentes.
3. **pgvector:** crie a extensão `vector` via migration. Crie tabela `perfis_vetoriais(usuario TEXT PK, nome TEXT, embedding vector(N))` onde `N` = número de dimensões do schema (derive de `dimensoes_schema_vetorial()` em `database.py`, hoje psicológico+valores+interesses). Crie índice apropriado (`ivfflat`/`hnsw` com `vector_cosine_ops`).
4. **Reescreva a camada de dados.** Crie `src/services/postgres_db.py` (ou refatore `sqlite_db.py`) reimplementando **todas** as funções públicas hoje usadas por `api.py` mantendo as mesmas assinaturas e formatos de retorno (ex.: `criar_match_usuario`, `confirmar_match`, `listar_matches_usuario`, `salvar_mensagem_match`, `obter_historico_match`, `salvar_vetores_sqlite`, `obter_ultimo_vetor_sqlite`, `obter_historico_chat`, `salvar_perfil_publico`, `obter_perfil_publico`, `listar_perfis_publicos`, `registrar_acao_match`, `obter_acao_match`, `listar_ids_indisponiveis_match`, `registrar_log_api`, `obter_logs_api`, e a classe `SQLiteUserRepository` → renomeie para `PostgresUserRepository` implementando `IUserRepository`). Use **sessões SQLAlchemy com pool de conexões**; uma sessão por request (dependency do FastAPI), commit/rollback corretos.
5. **Reescreva a busca vetorial** de `database.py` (`obter_colecao_usuarios`, `salvar_perfil_usuario`, `salvar_perfil_vetorial`, `obter_vetor_usuario`, `buscar_melhor_match`, `popular_banco_mock`) para usar pgvector via SQLAlchemy. Mantenha a lógica de `calcular_afinidade_mascarada` / `calcular_dimensoes_mais_proximas` / valores neutros 0.5 intacta — só troque o armazenamento/consulta de Chroma para pgvector (use distância coseno na query e depois aplique o mascaramento existente).
6. **Elimine o antipadrão `iniciar_banco_sqlite()` chamado em toda função.** A criação de schema deve ser feita **só via Alembic migrations**, não a cada chamada. Crie o schema inicial com `alembic revision --autogenerate` + `alembic upgrade head`.
7. **Migrations Alembic:** configure `alembic/`, `env.py` lendo `DATABASE_URL` do `settings`. Crie a migration inicial com todas as tabelas + extensão `vector` + índices.
8. **Script de seed** `scripts/seed.py` que popula os perfis mock (Maria, Carmen, Lia) no Postgres (relacional + vetorial), substituindo `popular_banco_mock`. Rodar no startup só em `dev`, ou manualmente em `prod`.
9. **Script de migração de dados** `scripts/migrar_sqlite_para_postgres.py` (opcional) que lê o `banco_relacional.db` e o `banco_vetorial` atuais e transfere os dados existentes para o Postgres, para não perder o que já existe localmente.
10. Atualize `main.py` para usar `PostgresUserRepository` e remova qualquer chamada de criação de schema em runtime.

## Fase 3 — Autenticação real (JWT) na API

1. Hoje a API confia cegamente nos headers `X-Usuario-Email`/`X-Usuario-Nome` — **qualquer um pode se passar por qualquer usuário**. Substitua isso por JWT.
2. Crie endpoints `POST /auth/register` e `POST /auth/login` no FastAPI que usam o `LoginController`/repositório e, no login bem-sucedido, retornam um **access token JWT** assinado com `JWT_SECRET` contendo `sub` = e-mail do usuário (e claim `is_admin`).
3. Crie uma dependency `usuario_atual = Depends(get_current_user)` que valida o `Authorization: Bearer <token>`, decodifica o JWT e retorna `{email, nome, is_admin}`. **Substitua todos os `Header(X-Usuario-Email...)` dos endpoints** por essa dependency. Endpoints sem token válido → `401`.
4. Endpoints admin (`/perfis_mock`, criação de mock customizado) checam `is_admin` do token, não mais `usuario_eh_admin` por header.
5. Remova o comportamento de `normalizar_email_usuario` retornar e-mail padrão; sem usuário autenticado não há identidade.
6. Atualize `src/services/api_client.py` e as views Flet (`login_view.py`, etc.) para: no login chamar `/auth/login`, **guardar o token**, e enviar `Authorization: Bearer` em todas as chamadas (em vez dos headers `X-Usuario-*`). Trate expiração/401 redirecionando para login.

## Fase 4 — Prontidão de produção do FastAPI

1. **CORS:** adicione `CORSMiddleware` lendo `CORS_ALLOW_ORIGINS` do settings (o frontend Flet web roda em outra origem).
2. Adicione endpoint `GET /health` (verifica conexão com o banco) para health checks do orquestrador.
3. Garanta `lifespan` rodando migrations/seed só conforme `ENV`, sem recriar schema a cada request.
4. Configure logging estruturado (nível por env), e não vaze `str(erro)` cru ao cliente em produção — logue detalhes, retorne mensagem genérica.
5. Adicione tratamento de pool/timeout do banco e limites de tamanho de payload.

## Fase 5 — Docker e deploy

1. **`Dockerfile.api`** (FastAPI): base `python:3.11-slim`, instala deps, copia código, expõe a porta, comando `uvicorn src.controllers.api:app --host 0.0.0.0 --port 8000`. Use usuário não-root.
2. **`Dockerfile.web`** (Flet web): builda/serve o frontend Flet em modo web (`flet` web) apontando `MATCHAI_API_BASE_URL` para o serviço da API.
3. **`docker-compose.yml`** com três serviços: `db` (imagem `pgvector/pgvector:pg16` com volume persistente e healthcheck), `api` (depende de `db` saudável, roda migrations no entrypoint, lê `DATABASE_URL`), `web`. Variáveis via `.env`.
4. Crie `entrypoint.sh` da API que espera o Postgres, roda `alembic upgrade head` e (em dev) o seed, depois sobe o uvicorn.
5. Adicione `.dockerignore` (`.git`, `__pycache__`, `*.db`, `banco_vetorial`, `.venv`, `tests`, `.env`).
6. Documente no README: deploy em Render/Railway/VPS (usar Postgres gerenciado com pgvector — ex.: Neon/Supabase/RDS —, setar `DATABASE_URL`, `JWT_SECRET`, `GROQ_API_KEY`, `CORS_ALLOW_ORIGINS`).

## Fase 6 — Testes, qualidade e documentação

1. **Atualize os testes** (`tests/`, ~1800 linhas) para a nova camada de dados e auth: use um Postgres de teste (container ou `pytest` fixture com banco descartável) ou SQLAlchemy com transação revertida por teste. Adapte os testes de `sqlite_db`, `api`, `database`, `login_view` para tokens JWT em vez de headers.
2. Adicione testes para: login/registro, rejeição de request sem token (401), bloqueio de admin para não-admin (403), busca vetorial com pgvector retornando afinidade correta.
3. Adicione `ruff` (lint+format) e configure no `pyproject.toml`; rode e corrija os apontamentos.
4. Adicione um workflow de CI (`.github/workflows/ci.yml`) que sobe Postgres+pgvector, roda migrations, lint e `pytest`.
5. Atualize o `README.md`: stack nova, variáveis de ambiente, como rodar com Docker Compose, como rodar migrations/seed, como rodar testes.

## Critérios de aceite (verifique ao final)

- `docker compose up` sobe `db` + `api` + `web` e a API responde em `/health` com banco conectado.
- Nenhum `.db`, `.env`, `banco_vetorial/`, log ou `__pycache__` versionado; `.env.example` presente.
- Nenhum dado pessoal hardcoded em `user_context.py` ou `llm_service.py`.
- Toda rota protegida exige `Authorization: Bearer` válido; headers `X-Usuario-*` removidos.
- Schema criado/evoluído **apenas** por Alembic; nada de `CREATE TABLE` em runtime por request.
- Busca de match funciona via pgvector com a mesma lógica de afinidade mascarada.
- `pytest` passa; `ruff` limpo.
- README atualizado.

Ao concluir cada fase, rode os testes da fase e faça commit. No final, me entregue: (1) resumo das mudanças por fase, (2) lista de variáveis de ambiente a configurar no host, (3) o lembrete de **revogar a GROQ_API_KEY exposta**, e (4) o passo-a-passo de deploy.

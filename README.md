# MatchAI

App de namoro com onboarding por IA, perfil vetorial dinamico, filtros de valores e matches por proximidade.

## Desenvolvimento

1. Copie `.env.example` para `.env` e preencha as chaves desejadas.
2. Suba o PostgreSQL local:

```bash
docker compose up -d postgres
```

3. Instale as dependencias e rode a API:

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

4. Em outro terminal, rode o app Flet:

```bash
python main.py
```

## Migracao opcional do SQLite legado

Com o PostgreSQL ativo:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite-path banco_relacional.db
```

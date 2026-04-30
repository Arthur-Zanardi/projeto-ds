# MatchAI

App de namoro com onboarding por IA, perfil vetorial dinamico, vetores fisicos, atracao cruzada, filtros de valores e matches por proximidade.

## Rodar com um comando

1. Copie `.env.example` para `.env` e preencha as chaves desejadas.
2. No Windows, de dois cliques em `start_matchai.bat` ou rode:

```bash
python scripts/run_matchai.py
```

O launcher verifica o PostgreSQL, tenta iniciar `docker compose up -d postgres` quando Docker estiver disponivel, sobe a API FastAPI em background e abre o Flet. Se nao houver PostgreSQL nem Docker nesta maquina, ele roda em modo local com `matchai_local.db` para desenvolvimento.

Evite abrir `python main.py` diretamente para uso normal, porque esse comando abre apenas a interface e nao inicia a API.

## Gerar executavel

No PowerShell:

```powershell
.\scripts\build_exe.ps1
```

O artefato sera gerado em `dist/MatchAI.exe`.

## Desenvolvimento manual

```bash
docker compose up -d postgres
pip install -r requirements.txt
uvicorn api:app --reload
python main.py
```

## Migracao opcional do SQLite legado

Com o PostgreSQL ativo:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite-path banco_relacional.db
```

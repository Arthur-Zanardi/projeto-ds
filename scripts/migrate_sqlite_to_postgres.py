from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.postgres_db import migrate_sqlite_to_postgres


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migra o banco_relacional.db legado para o PostgreSQL do MatchAI."
    )
    parser.add_argument("--sqlite-path", default="banco_relacional.db")
    parser.add_argument("--legacy-email", default="legado@matchai.local")
    args = parser.parse_args()

    result = migrate_sqlite_to_postgres(
        sqlite_path=args.sqlite_path,
        legacy_email=args.legacy_email,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

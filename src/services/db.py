from __future__ import annotations

import os


BACKEND = os.getenv("MATCHAI_DB_BACKEND", "postgres").lower().strip()

if BACKEND == "sqlite":
    from src.services.local_db import *  # noqa: F403
else:
    from src.services.postgres_db import *  # noqa: F403

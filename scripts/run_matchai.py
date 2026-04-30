from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
else:
    APP_ROOT = Path(__file__).resolve().parents[1]
    RESOURCE_ROOT = APP_ROOT

for path in (APP_ROOT, RESOURCE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.chdir(APP_ROOT)
load_dotenv(RESOURCE_ROOT / ".env.example")
load_dotenv(APP_ROOT / ".env", override=True)

API_HOST = os.getenv("MATCHAI_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("MATCHAI_API_PORT", "8000"))
API_URL = f"http://{API_HOST}:{API_PORT}"


def database_host_port() -> tuple[str, int]:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://matchai:matchai@127.0.0.1:5432/matchai",
    )
    parsed = urllib.parse.urlparse(database_url)
    return parsed.hostname or "127.0.0.1", parsed.port or 5432


def can_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_postgres() -> None:
    if os.getenv("MATCHAI_DB_BACKEND", "").lower() == "sqlite":
        print("Usando banco local SQLite por MATCHAI_DB_BACKEND=sqlite.")
        return

    host, port = database_host_port()
    if can_connect(host, port):
        os.environ["MATCHAI_DB_BACKEND"] = "postgres"
        return

    docker = shutil.which("docker")
    compose_file = RESOURCE_ROOT / "docker-compose.yml"
    if docker and compose_file.exists():
        print("PostgreSQL nao respondeu. Tentando iniciar via Docker Compose...")
        subprocess.run(
            [docker, "compose", "-f", str(compose_file), "up", "-d", "postgres"],
            cwd=APP_ROOT,
            check=False,
        )
        for _ in range(45):
            if can_connect(host, port):
                os.environ["MATCHAI_DB_BACKEND"] = "postgres"
                return
            time.sleep(1)

    if os.getenv("MATCHAI_REQUIRE_POSTGRES", "").lower() in {"1", "true", "yes"}:
        raise SystemExit(
            "PostgreSQL nao esta acessivel. Inicie o Docker Desktop ou configure DATABASE_URL no .env."
        )

    os.environ["MATCHAI_DB_BACKEND"] = "sqlite"
    os.environ.setdefault("MATCHAI_SQLITE_PATH", str(APP_ROOT / "matchai_local.db"))
    print(
        "PostgreSQL/Docker nao encontrado. "
        "Rodando em modo local com SQLite para desenvolvimento."
    )


def start_api_thread():
    import api
    import uvicorn

    config = uvicorn.Config(api.app, host=API_HOST, port=API_PORT, log_level="info")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def wait_for_api() -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{API_URL}/", timeout=1) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(1)
    raise SystemExit("API do MatchAI nao iniciou a tempo.")


def main() -> None:
    ensure_postgres()
    server, thread = start_api_thread()
    wait_for_api()

    os.environ["MATCHAI_API_URL"] = API_URL
    import flet as ft
    import main as flet_main

    try:
        ft.run(flet_main.main)
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()

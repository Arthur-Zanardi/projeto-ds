import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "banco_relacional.db"
logger = logging.getLogger(__name__)


def conectar():
    return sqlite3.connect(DB_PATH)


def iniciar_banco_sqlite():
    logger.info("Banco SQLite em uso: %s", DB_PATH)

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            remetente TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vetores_salvos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            vetores_json TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_api (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            acao TEXT NOT NULL,
            status TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            detalhes_json TEXT,
            data_hora TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def salvar_mensagem(usuario: str, remetente: str, mensagem: str):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO historico_chat 
        (usuario, remetente, mensagem, data_hora) 
        VALUES (?, ?, ?, ?)
        """,
        (usuario, remetente, mensagem, data_hora)
    )

    conn.commit()
    conn.close()

    logger.info(
        "Mensagem salva no SQLite: %s | %s | %s",
        usuario,
        remetente,
        mensagem[:50],
    )


def salvar_vetores_sqlite(usuario: str, vetores_dict: dict):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vetores_json_str = json.dumps(vetores_dict, ensure_ascii=False)

    cursor.execute(
        """
        INSERT INTO vetores_salvos 
        (usuario, vetores_json, data_hora) 
        VALUES (?, ?, ?)
        """,
        (usuario, vetores_json_str, data_hora)
    )

    conn.commit()
    conn.close()

    logger.info("Vetores salvos no SQLite para usuario: %s", usuario)


def obter_ultimo_vetor_sqlite(usuario: str = "user_rafaell"):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT vetores_json
        FROM vetores_salvos
        WHERE usuario = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (usuario,)
    )

    resultado = cursor.fetchone()
    conn.close()

    if resultado is None:
        return None

    return json.loads(resultado[0])


def obter_historico_chat(usuario: str = "user_rafaell"):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT remetente, mensagem 
        FROM historico_chat 
        WHERE usuario = ? 
        ORDER BY id ASC
        """,
        (usuario,)
    )

    mensagens = cursor.fetchall()
    conn.close()

    return [
        {"remetente": remetente, "mensagem": mensagem}
        for remetente, mensagem in mensagens
    ]


def registrar_log_api(
    usuario: str,
    endpoint: str,
    acao: str,
    status: str,
    mensagem: str,
    detalhes: dict | None = None,
):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detalhes_json = (
        json.dumps(detalhes, ensure_ascii=False)
        if detalhes is not None
        else None
    )

    cursor.execute(
        """
        INSERT INTO logs_api
        (usuario, endpoint, acao, status, mensagem, detalhes_json, data_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario,
            endpoint,
            acao,
            status,
            mensagem,
            detalhes_json,
            data_hora,
        )
    )

    conn.commit()
    conn.close()

    logger.info(
        "Log API registrado: %s | %s | %s | %s",
        usuario,
        endpoint,
        acao,
        status,
    )


def obter_logs_api(usuario: str = "user_rafaell"):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT endpoint, acao, status, mensagem, detalhes_json, data_hora
        FROM logs_api
        WHERE usuario = ?
        ORDER BY id ASC
        """,
        (usuario,)
    )

    logs = cursor.fetchall()
    conn.close()

    return [
        {
            "endpoint": endpoint,
            "acao": acao,
            "status": status,
            "mensagem": mensagem,
            "detalhes": json.loads(detalhes_json) if detalhes_json else None,
            "data_hora": data_hora,
        }
        for endpoint, acao, status, mensagem, detalhes_json, data_hora in logs
    ]

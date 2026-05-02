import sqlite3
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "banco_relacional.db"


def conectar():
    return sqlite3.connect(DB_PATH)


def iniciar_banco_sqlite():
    print(f"Banco SQLite em uso: {DB_PATH}")

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

    print(f"Mensagem salva no SQLite: {usuario} | {remetente} | {mensagem[:50]}")


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

    print(f"Vetores salvos no SQLite para usuário: {usuario}")


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
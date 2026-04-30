import sqlite3
import json
from datetime import datetime

DB_PATH = "banco_relacional.db"

def iniciar_banco_sqlite():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            remetente TEXT,
            mensagem TEXT,
            data_hora TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vetores_salvos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            vetores_json TEXT,
            data_hora TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_mensagem(usuario: str, remetente: str, mensagem: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO historico_chat (usuario, remetente, mensagem, data_hora) VALUES (?, ?, ?, ?)",
        (usuario, remetente, mensagem, data_hora)
    )
    conn.commit()
    conn.close()

def salvar_vetores_sqlite(usuario: str, vetores_dict: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vetores_json_str = json.dumps(vetores_dict, ensure_ascii=False)
    cursor.execute(
        "INSERT INTO vetores_salvos (usuario, vetores_json, data_hora) VALUES (?, ?, ?)",
        (usuario, vetores_json_str, data_hora)
    )
    conn.commit()
    conn.close()

def obter_historico_chat(usuario: str = "user_rafaell"):
    """Lê todas as mensagens de um usuário específico para recarregar o chat"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT remetente, mensagem FROM historico_chat WHERE usuario = ? ORDER BY id ASC",
        (usuario,)
    )
    mensagens = cursor.fetchall()
    conn.close()
    
    # Formata como uma lista de dicionários para a API enviar ao Flet
    return [{"remetente": msg[0], "mensagem": msg[1]} for msg in mensagens]
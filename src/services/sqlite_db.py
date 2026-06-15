import sqlite3
import json
import logging
import bcrypt
from datetime import datetime
from pathlib import Path

# Certifique-se de ter criado o arquivo database.py com a classe IUserRepository
from src.services.interfaces import IUserRepository 

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "banco_relacional.db"
logger = logging.getLogger(__name__)

def conectar():
    conn = sqlite3.connect(DB_PATH)
    # Ativa o modo WAL para permitir concorrência no SQLite inteiro (Escalabilidade)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def iniciar_banco_sqlite():
    logger.info("Banco SQLite em uso: %s", DB_PATH)

    conn = conectar()
    cursor = conn.cursor()

    # 1. Tabela de Chat 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            remetente TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    # 2. Tabela de Vetores 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vetores_salvos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            vetores_json TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    # 3. Tabela de Logs 
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

    # 4. Tabela de Usuários para o Login
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# =====================================================================

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
    logger.info("Mensagem salva no SQLite: %s | %s | %s", usuario, remetente, mensagem[:50])

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
    return [{"remetente": remetente, "mensagem": mensagem} for remetente, mensagem in mensagens]

def registrar_log_api(usuario: str, endpoint: str, acao: str, status: str, mensagem: str, detalhes: dict | None = None):
    iniciar_banco_sqlite()
    conn = conectar()
    cursor = conn.cursor()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detalhes_json = json.dumps(detalhes, ensure_ascii=False) if detalhes is not None else None
    cursor.execute(
        """
        INSERT INTO logs_api
        (usuario, endpoint, acao, status, mensagem, detalhes_json, data_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (usuario, endpoint, acao, status, mensagem, detalhes_json, data_hora)
    )
    conn.commit()
    conn.close()
    logger.info("Log API registrado: %s | %s | %s | %s", usuario, endpoint, acao, status)

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
            "endpoint": endpoint, "acao": acao, "status": status, "mensagem": mensagem,
            "detalhes": json.loads(detalhes_json) if detalhes_json else None, "data_hora": data_hora,
        }
        for endpoint, acao, status, mensagem, detalhes_json, data_hora in logs
    ]

# =====================================================================
# NOVA CLASSE DE AUTENTICAÇÃO (O "D" do SOLID)
# =====================================================================

class SQLiteUserRepository(IUserRepository):
    def __init__(self):
        # Garante que as tabelas existem sempre que a classe for instanciada
        iniciar_banco_sqlite()

    def criar_usuario(self, nome: str, email: str, senha_pura: str) -> bool:
        # Criptografa a senha antes de salvar
        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(senha_pura.encode('utf-8'), salt).decode('utf-8')

        query = "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)"
        try:
            conn = conectar()
            conn.execute(query, (nome, email, senha_hash))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False # Retorna falso se o email já estiver cadastrado

    def buscar_usuario_por_email(self, email: str) -> dict:
        query = "SELECT * FROM usuarios WHERE email = ?"
        conn = conectar()
        # Retorna os dados como dicionário em vez de tupla para facilitar o uso no Flet
        conn.row_factory = sqlite3.Row 
        
        cursor = conn.execute(query, (email,))
        linha = cursor.fetchone()
        conn.close()
        
        return dict(linha) if linha else None
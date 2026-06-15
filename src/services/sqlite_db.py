import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "banco_relacional.db"
logger = logging.getLogger(__name__)


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
        CREATE TABLE IF NOT EXISTS matches_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            match_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            afinidade TEXT,
            dados_match_json TEXT,
            data_hora TEXT NOT NULL,
            UNIQUE(usuario, match_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensagens_match (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            match_id TEXT NOT NULL,
            remetente TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (usuario, match_id)
                REFERENCES matches_usuario(usuario, match_id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_usuario_usuario
        ON matches_usuario(usuario)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_mensagens_match_usuario_match
        ON mensagens_match(usuario, match_id, id)
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


def _formatar_match(row):
    if row is None:
        return None

    (
        id_match,
        usuario,
        match_id,
        nome,
        afinidade,
        dados_match_json,
        data_hora,
    ) = row

    return {
        "id": id_match,
        "usuario": usuario,
        "match_id": match_id,
        "nome": nome,
        "afinidade": afinidade,
        "dados_match": json.loads(dados_match_json)
        if dados_match_json
        else None,
        "data_hora": data_hora,
    }


def criar_match_usuario(
    usuario: str,
    match_id: str,
    nome: str,
    afinidade: str | None = None,
    dados_match: dict | None = None,
):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dados_match_json = (
        json.dumps(dados_match, ensure_ascii=False)
        if dados_match is not None
        else None
    )

    cursor.execute(
        """
        INSERT INTO matches_usuario
        (usuario, match_id, nome, afinidade, dados_match_json, data_hora)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario, match_id) DO UPDATE SET
            nome = excluded.nome,
            afinidade = excluded.afinidade,
            dados_match_json = excluded.dados_match_json,
            data_hora = excluded.data_hora
        """,
        (
            usuario,
            match_id,
            nome,
            afinidade,
            dados_match_json,
            data_hora,
        ),
    )

    conn.commit()

    cursor.execute(
        """
        SELECT id, usuario, match_id, nome, afinidade, dados_match_json, data_hora
        FROM matches_usuario
        WHERE usuario = ? AND match_id = ?
        """,
        (usuario, match_id),
    )
    match = _formatar_match(cursor.fetchone())
    conn.close()

    logger.info("Match salvo no SQLite: %s | %s", usuario, match_id)
    return match


def obter_match_usuario(usuario: str, match_id: str):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, usuario, match_id, nome, afinidade, dados_match_json, data_hora
        FROM matches_usuario
        WHERE usuario = ? AND match_id = ?
        """,
        (usuario, match_id),
    )

    match = _formatar_match(cursor.fetchone())
    conn.close()
    return match


def listar_matches_usuario(usuario: str = "user_rafaell"):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, usuario, match_id, nome, afinidade, dados_match_json, data_hora
        FROM matches_usuario
        WHERE usuario = ?
        ORDER BY id ASC
        """,
        (usuario,),
    )

    matches = [_formatar_match(row) for row in cursor.fetchall()]
    conn.close()
    return matches


def salvar_mensagem_match(
    usuario: str,
    match_id: str,
    remetente: str,
    mensagem: str,
):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM matches_usuario
        WHERE usuario = ? AND match_id = ?
        """,
        (usuario, match_id),
    )

    if cursor.fetchone() is None:
        conn.close()
        raise ValueError("Match nao encontrado.")

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO mensagens_match
        (usuario, match_id, remetente, mensagem, data_hora)
        VALUES (?, ?, ?, ?, ?)
        """,
        (usuario, match_id, remetente, mensagem, data_hora),
    )

    conn.commit()
    conn.close()

    logger.info(
        "Mensagem de match salva no SQLite: %s | %s | %s",
        usuario,
        match_id,
        remetente,
    )


def obter_historico_match(usuario: str, match_id: str):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT remetente, mensagem
        FROM mensagens_match
        WHERE usuario = ? AND match_id = ?
        ORDER BY id ASC
        """,
        (usuario, match_id),
    )

    mensagens = cursor.fetchall()
    conn.close()

    return [
        {"remetente": remetente, "mensagem": mensagem}
        for remetente, mensagem in mensagens
    ]


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

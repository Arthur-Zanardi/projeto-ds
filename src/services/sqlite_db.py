import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import bcrypt

from src.services.interfaces import IUserRepository
from src.services.profile_completion import FOTO_PADRAO
from src.services.user_context import (
    EMAIL_USUARIO_PADRAO,
    USUARIO_LEGADO,
    normalizar_email_usuario,
    normalizar_nome_usuario,
)


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "banco_relacional.db"
logger = logging.getLogger(__name__)

def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _normalizar_identificador(valor: str | None) -> str:
    return str(valor or "").strip().lower()


def _normalizar_email_obrigatorio(email: str | None) -> str:
    email_normalizado = _normalizar_identificador(email)
    return email_normalizado if email_normalizado else ""


def _adicionar_coluna(cursor, tabela: str, coluna: str, definicao: str):
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas = {row["name"] for row in cursor.fetchall()}

    if coluna not in colunas:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def _gerar_conversa_id(participante_a: str, participante_b: str) -> str:
    primeiro, segundo = sorted(
        [_normalizar_identificador(participante_a), _normalizar_identificador(participante_b)]
    )
    digest = hashlib.sha1(f"{primeiro}|{segundo}".encode("utf-8")).hexdigest()[:16]
    return f"conv_{digest}"


def _agora_sqlite():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def agora_sqlite():
    return _agora_sqlite()


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
        CREATE TABLE IF NOT EXISTS conversas_match (
            conversa_id TEXT PRIMARY KEY,
            participante_1 TEXT NOT NULL,
            participante_2 TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'real',
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
            conversa_id TEXT,
            UNIQUE(usuario, match_id),
            FOREIGN KEY (conversa_id)
                REFERENCES conversas_match(conversa_id)
                ON DELETE SET NULL
        )
    """)
    _adicionar_coluna(cursor, "matches_usuario", "conversa_id", "TEXT")

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
        CREATE TABLE IF NOT EXISTS mensagens_conversa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id TEXT NOT NULL,
            remetente TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (conversa_id)
                REFERENCES conversas_match(conversa_id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfis_publicos (
            usuario TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            idade INTEGER,
            foto_url TEXT,
            descricao TEXT,
            localizacao TEXT,
            cargo TEXT,
            origem TEXT NOT NULL DEFAULT 'real',
            mock_customizado INTEGER NOT NULL DEFAULT 0,
            data_hora TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acoes_match (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            candidato_id TEXT NOT NULL,
            acao TEXT NOT NULL CHECK(acao IN ('like', 'pass')),
            data_hora TEXT NOT NULL,
            UNIQUE(usuario, candidato_id)
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
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
        CREATE INDEX IF NOT EXISTS idx_mensagens_conversa_conversa
        ON mensagens_conversa(conversa_id, id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_acoes_match_usuario
        ON acoes_match(usuario, candidato_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_perfis_publicos_origem
        ON perfis_publicos(origem)
    """)

    _normalizar_emails_usuarios(cursor)
    _migrar_usuario_legado_sqlite(cursor)
    _migrar_conversas_legadas(cursor)

    conn.commit()
    conn.close()


def _normalizar_emails_usuarios(cursor):
    cursor.execute("SELECT id, email FROM usuarios")
    for row in cursor.fetchall():
        email_normalizado = _normalizar_identificador(row["email"])
        if email_normalizado and email_normalizado != row["email"]:
            try:
                cursor.execute(
                    "UPDATE usuarios SET email = ? WHERE id = ?",
                    (email_normalizado, row["id"]),
                )
            except sqlite3.IntegrityError:
                logger.warning("E-mail duplicado apos normalizacao: %s", row["email"])


def _migrar_usuario_legado_sqlite(
    cursor,
    origem: str = USUARIO_LEGADO,
    destino: str = EMAIL_USUARIO_PADRAO,
):
    destino = normalizar_email_usuario(destino)

    if origem == destino:
        return

    cursor.execute(
        """
        INSERT OR IGNORE INTO matches_usuario
        (usuario, match_id, nome, afinidade, dados_match_json, data_hora, conversa_id)
        SELECT ?, match_id, nome, afinidade, dados_match_json, data_hora, conversa_id
        FROM matches_usuario
        WHERE usuario = ?
        """,
        (destino, origem),
    )

    cursor.execute(
        """
        UPDATE mensagens_match
        SET usuario = ?
        WHERE usuario = ?
        """,
        (destino, origem),
    )

    cursor.execute(
        """
        DELETE FROM matches_usuario
        WHERE usuario = ?
        """,
        (origem,),
    )

    for tabela in ("historico_chat", "vetores_salvos", "logs_api"):
        cursor.execute(
            f"""
            UPDATE {tabela}
            SET usuario = ?
            WHERE usuario = ?
            """,
            (destino, origem),
        )

    cursor.execute(
        """
        INSERT OR IGNORE INTO perfis_publicos
        (usuario, nome, idade, foto_url, descricao, localizacao, cargo,
         origem, mock_customizado, data_hora)
        SELECT ?, nome, idade, foto_url, descricao, localizacao, cargo,
               origem, mock_customizado, data_hora
        FROM perfis_publicos
        WHERE usuario = ?
        """,
        (destino, origem),
    )
    cursor.execute("DELETE FROM perfis_publicos WHERE usuario = ?", (origem,))

    cursor.execute(
        """
        INSERT OR IGNORE INTO acoes_match
        (usuario, candidato_id, acao, data_hora)
        SELECT ?, candidato_id, acao, data_hora
        FROM acoes_match
        WHERE usuario = ?
        """,
        (destino, origem),
    )
    cursor.execute("DELETE FROM acoes_match WHERE usuario = ?", (origem,))


def _migrar_conversas_legadas(cursor):
    cursor.execute(
        """
        SELECT usuario, match_id
        FROM matches_usuario
        WHERE conversa_id IS NULL OR conversa_id = ''
        """
    )
    for row in cursor.fetchall():
        usuario = _normalizar_identificador(row["usuario"])
        match_id = _normalizar_identificador(row["match_id"])
        conversa_id = _gerar_conversa_id(usuario, match_id)
        tipo = "real" if "@" in match_id else "mock"
        cursor.execute(
            """
            INSERT OR IGNORE INTO conversas_match
            (conversa_id, participante_1, participante_2, tipo, data_hora)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversa_id, usuario, match_id, tipo, _agora_sqlite()),
        )
        cursor.execute(
            """
            UPDATE matches_usuario
            SET conversa_id = ?
            WHERE usuario = ? AND match_id = ?
            """,
            (conversa_id, usuario, match_id),
        )

    cursor.execute(
        """
        SELECT mm.usuario, mm.match_id, mm.remetente, mm.mensagem, mm.data_hora,
               mu.conversa_id
        FROM mensagens_match mm
        JOIN matches_usuario mu
          ON mu.usuario = mm.usuario AND mu.match_id = mm.match_id
        WHERE mu.conversa_id IS NOT NULL
        """
    )
    for row in cursor.fetchall():
        remetente = row["remetente"]
        if remetente == "usuario":
            remetente = row["usuario"]
        elif remetente == "match":
            remetente = row["match_id"]

        cursor.execute(
            """
            INSERT INTO mensagens_conversa
            (conversa_id, remetente, mensagem, data_hora)
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1
                FROM mensagens_conversa
                WHERE conversa_id = ?
                  AND remetente = ?
                  AND mensagem = ?
                  AND data_hora = ?
            )
            """,
            (
                row["conversa_id"],
                remetente,
                row["mensagem"],
                row["data_hora"],
                row["conversa_id"],
                remetente,
                row["mensagem"],
                row["data_hora"],
            ),
        )


def migrar_usuario_legado_sqlite(
    origem: str = USUARIO_LEGADO,
    destino: str = EMAIL_USUARIO_PADRAO,
):
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()
    _migrar_usuario_legado_sqlite(cursor, origem=origem, destino=destino)
    _migrar_conversas_legadas(cursor)
    conn.commit()
    conn.close()


def salvar_mensagem(usuario: str, remetente: str, mensagem: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO historico_chat
        (usuario, remetente, mensagem, data_hora)
        VALUES (?, ?, ?, ?)
        """,
        (usuario, remetente, mensagem, _agora_sqlite()),
    )

    conn.commit()
    conn.close()

    logger.info("Mensagem salva no SQLite: %s | %s | %s", usuario, remetente, mensagem[:50])


def _formatar_match(row):
    if row is None:
        return None

    dados_match_json = row["dados_match_json"]
    dados_match = json.loads(dados_match_json) if dados_match_json else None

    return {
        "id": row["id"],
        "usuario": row["usuario"],
        "match_id": row["match_id"],
        "nome": row["nome"],
        "afinidade": row["afinidade"],
        "dados_match": dados_match,
        "data_hora": row["data_hora"],
        "conversa_id": row["conversa_id"],
    }


def _dados_match_com_conversa(
    dados_match: dict | None,
    match_id: str,
    nome: str,
    conversa_id: str,
):
    if dados_match is None:
        return None

    return dict(dados_match)


def criar_match_usuario(
    usuario: str,
    match_id: str,
    nome: str,
    afinidade: str | None = None,
    dados_match: dict | None = None,
    conversa_id: str | None = None,
    tipo: str = "mock",
):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    conversa_id = conversa_id or _gerar_conversa_id(usuario, match_id)

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO conversas_match
        (conversa_id, participante_1, participante_2, tipo, data_hora)
        VALUES (?, ?, ?, ?, ?)
        """,
        (conversa_id, usuario, match_id, tipo, _agora_sqlite()),
    )

    dados = _dados_match_com_conversa(dados_match, match_id, nome, conversa_id)
    dados_match_json = json.dumps(dados, ensure_ascii=False) if dados is not None else None

    cursor.execute(
        """
        INSERT INTO matches_usuario
        (usuario, match_id, nome, afinidade, dados_match_json, data_hora, conversa_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario, match_id) DO UPDATE SET
            nome = excluded.nome,
            afinidade = excluded.afinidade,
            dados_match_json = excluded.dados_match_json,
            data_hora = excluded.data_hora,
            conversa_id = excluded.conversa_id
        """,
        (usuario, match_id, nome, afinidade, dados_match_json, _agora_sqlite(), conversa_id),
    )

    conn.commit()

    cursor.execute(
        """
        SELECT id, usuario, match_id, nome, afinidade, dados_match_json, data_hora, conversa_id
        FROM matches_usuario
        WHERE usuario = ? AND match_id = ?
        """,
        (usuario, match_id),
    )
    match = _formatar_match(cursor.fetchone())
    conn.close()

    logger.info("Match salvo no SQLite: %s | %s", usuario, match_id)
    return match


def confirmar_match(
    usuario: str,
    candidato_id: str,
    perfil_candidato: dict,
    perfil_usuario: dict | None = None,
    tipo: str = "real",
    sugestoes: list[dict] | None = None,
):
    usuario = normalizar_email_usuario(usuario)
    candidato_id = _normalizar_identificador(candidato_id)
    conversa_id = _gerar_conversa_id(usuario, candidato_id)
    sugestoes = sugestoes or []

    dados_candidato = dict(perfil_candidato or {})
    dados_candidato.update({
        "id": candidato_id,
        "match_id": candidato_id,
        "tipo": tipo,
        "match_confirmado": True,
        "sugestoes_inicio": sugestoes,
    })
    match_usuario = criar_match_usuario(
        usuario=usuario,
        match_id=candidato_id,
        nome=dados_candidato.get("nome") or normalizar_nome_usuario(None, candidato_id),
        afinidade=dados_candidato.get("afinidade"),
        dados_match=dados_candidato,
        conversa_id=conversa_id,
        tipo=tipo,
    )

    if tipo == "real":
        perfil_usuario = dict(perfil_usuario or obter_perfil_publico(usuario) or {})
        perfil_usuario.update({
            "id": usuario,
            "match_id": usuario,
            "tipo": tipo,
            "match_confirmado": True,
            "sugestoes_inicio": sugestoes,
        })
        criar_match_usuario(
            usuario=candidato_id,
            match_id=usuario,
            nome=perfil_usuario.get("nome") or normalizar_nome_usuario(None, usuario),
            afinidade=perfil_usuario.get("afinidade"),
            dados_match=perfil_usuario,
            conversa_id=conversa_id,
            tipo=tipo,
        )

    return match_usuario


def obter_match_usuario(usuario: str, match_id: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, usuario, match_id, nome, afinidade, dados_match_json, data_hora, conversa_id
        FROM matches_usuario
        WHERE usuario = ? AND match_id = ?
        """,
        (usuario, match_id),
    )

    match = _formatar_match(cursor.fetchone())
    conn.close()
    return match


def listar_matches_usuario(usuario: str = EMAIL_USUARIO_PADRAO):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, usuario, match_id, nome, afinidade, dados_match_json, data_hora, conversa_id
        FROM matches_usuario
        WHERE usuario = ?
        ORDER BY id ASC
        """,
        (usuario,),
    )

    matches = [_formatar_match(row) for row in cursor.fetchall()]
    conn.close()
    return matches


def salvar_mensagem_match(usuario: str, match_id: str, remetente: str, mensagem: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    match = obter_match_usuario(usuario, match_id)

    if match is None:
        raise ValueError("Match nao encontrado.")

    remetente_normalizado = remetente
    if remetente == "usuario":
        remetente_normalizado = usuario
    elif remetente == "match":
        remetente_normalizado = match_id

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mensagens_conversa
        (conversa_id, remetente, mensagem, data_hora)
        VALUES (?, ?, ?, ?)
        """,
        (match["conversa_id"], remetente_normalizado, mensagem, _agora_sqlite()),
    )

    conn.commit()
    conn.close()

    logger.info("Mensagem de match salva: %s | %s | %s", usuario, match_id, remetente)


def obter_historico_match(usuario: str, match_id: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    match_id = _normalizar_identificador(match_id)
    match = obter_match_usuario(usuario, match_id)

    if match is None:
        return []

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT remetente, mensagem
        FROM mensagens_conversa
        WHERE conversa_id = ?
        ORDER BY id ASC
        """,
        (match["conversa_id"],),
    )
    mensagens = cursor.fetchall()
    conn.close()

    return [
        {
            "remetente": "usuario" if row["remetente"] == usuario else "match",
            "mensagem": row["mensagem"],
        }
        for row in mensagens
    ]


def salvar_vetores_sqlite(usuario: str, vetores_dict: dict):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()
    vetores_json_str = json.dumps(vetores_dict, ensure_ascii=False)

    cursor.execute(
        """
        INSERT INTO vetores_salvos
        (usuario, vetores_json, data_hora)
        VALUES (?, ?, ?)
        """,
        (usuario, vetores_json_str, _agora_sqlite()),
    )

    conn.commit()
    conn.close()

    logger.info("Vetores salvos no SQLite para usuario: %s", usuario)


def obter_ultimo_vetor_sqlite(usuario: str = EMAIL_USUARIO_PADRAO):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
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
        (usuario,),
    )

    resultado = cursor.fetchone()
    conn.close()

    if resultado is None:
        return None

    return json.loads(resultado["vetores_json"])


def obter_historico_chat(usuario: str = EMAIL_USUARIO_PADRAO):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT remetente, mensagem
        FROM historico_chat
        WHERE usuario = ?
        ORDER BY id ASC
        """,
        (usuario,),
    )

    mensagens = cursor.fetchall()
    conn.close()

    return [
        {"remetente": row["remetente"], "mensagem": row["mensagem"]}
        for row in mensagens
    ]


def salvar_perfil_publico(
    usuario: str,
    nome: str,
    idade: int | str | None = None,
    foto_url: str | None = None,
    descricao: str | None = None,
    localizacao: str | None = None,
    cargo: str | None = None,
    origem: str = "real",
    mock_customizado: bool = False,
):
    iniciar_banco_sqlite()

    usuario = _normalizar_identificador(usuario)
    if not usuario:
        raise ValueError("Usuario do perfil publico nao pode ser vazio.")

    try:
        idade_normalizada = int(idade) if idade not in (None, "") else None
    except (TypeError, ValueError):
        idade_normalizada = None

    nome_normalizado = (nome or "").strip() or normalizar_nome_usuario(None, usuario)
    foto_url = (foto_url or FOTO_PADRAO).strip()
    descricao = (descricao or "Perfil em construcao.").strip()
    localizacao = (localizacao or "Localizacao nao informada").strip()
    cargo = (cargo or "Explorando novas conexoes").strip()
    origem = (origem or "real").strip().lower()

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO perfis_publicos
        (usuario, nome, idade, foto_url, descricao, localizacao, cargo,
         origem, mock_customizado, data_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario) DO UPDATE SET
            nome = excluded.nome,
            idade = excluded.idade,
            foto_url = excluded.foto_url,
            descricao = excluded.descricao,
            localizacao = excluded.localizacao,
            cargo = excluded.cargo,
            origem = excluded.origem,
            mock_customizado = excluded.mock_customizado,
            data_hora = excluded.data_hora
        """,
        (
            usuario,
            nome_normalizado,
            idade_normalizada,
            foto_url,
            descricao,
            localizacao,
            cargo,
            origem,
            1 if mock_customizado else 0,
            _agora_sqlite(),
        ),
    )
    conn.commit()
    conn.close()

    return obter_perfil_publico(usuario)


def _formatar_perfil_publico(row):
    if row is None:
        return None

    return {
        "id": row["usuario"],
        "match_id": row["usuario"],
        "usuario": row["usuario"],
        "nome": row["nome"],
        "idade": row["idade"],
        "imagem": row["foto_url"] or FOTO_PADRAO,
        "foto_url": row["foto_url"] or FOTO_PADRAO,
        "descricao": row["descricao"] or "",
        "localizacao": row["localizacao"] or "",
        "cargo": row["cargo"] or "",
        "origem": row["origem"],
        "mock_customizado": bool(row["mock_customizado"]),
        "data_hora": row["data_hora"],
    }


def obter_perfil_publico(usuario: str):
    iniciar_banco_sqlite()

    usuario = _normalizar_identificador(usuario)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT usuario, nome, idade, foto_url, descricao, localizacao, cargo,
               origem, mock_customizado, data_hora
        FROM perfis_publicos
        WHERE usuario = ?
        """,
        (usuario,),
    )
    perfil = _formatar_perfil_publico(cursor.fetchone())
    conn.close()
    return perfil


def listar_perfis_publicos():
    iniciar_banco_sqlite()

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT usuario, nome, idade, foto_url, descricao, localizacao, cargo,
               origem, mock_customizado, data_hora
        FROM perfis_publicos
        ORDER BY nome ASC
        """
    )
    perfis = [_formatar_perfil_publico(row) for row in cursor.fetchall()]
    conn.close()
    return perfis


def registrar_acao_match(usuario: str, candidato_id: str, acao: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    candidato_id = _normalizar_identificador(candidato_id)
    acao = (acao or "").strip().lower()

    if acao not in {"like", "pass"}:
        raise ValueError("Acao de match invalida.")

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO acoes_match
        (usuario, candidato_id, acao, data_hora)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(usuario, candidato_id) DO UPDATE SET
            acao = excluded.acao,
            data_hora = excluded.data_hora
        """,
        (usuario, candidato_id, acao, _agora_sqlite()),
    )
    conn.commit()
    conn.close()

    return obter_acao_match(usuario, candidato_id)


def obter_acao_match(usuario: str, candidato_id: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    candidato_id = _normalizar_identificador(candidato_id)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT usuario, candidato_id, acao, data_hora
        FROM acoes_match
        WHERE usuario = ? AND candidato_id = ?
        """,
        (usuario, candidato_id),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "usuario": row["usuario"],
        "candidato_id": row["candidato_id"],
        "acao": row["acao"],
        "data_hora": row["data_hora"],
    }


def listar_ids_indisponiveis_match(usuario: str):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT candidato_id FROM acoes_match WHERE usuario = ?
        UNION
        SELECT match_id FROM matches_usuario WHERE usuario = ?
        """,
        (usuario, usuario),
    )
    ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return ids


def registrar_log_api(
    usuario: str,
    endpoint: str,
    acao: str,
    status: str,
    mensagem: str,
    detalhes: dict | None = None,
):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()
    detalhes_json = json.dumps(detalhes, ensure_ascii=False) if detalhes is not None else None

    cursor.execute(
        """
        INSERT INTO logs_api
        (usuario, endpoint, acao, status, mensagem, detalhes_json, data_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (usuario, endpoint, acao, status, mensagem, detalhes_json, _agora_sqlite()),
    )

    conn.commit()
    conn.close()

    logger.info("Log API registrado: %s | %s | %s | %s", usuario, endpoint, acao, status)


def obter_logs_api(usuario: str = EMAIL_USUARIO_PADRAO):
    iniciar_banco_sqlite()

    usuario = normalizar_email_usuario(usuario)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT endpoint, acao, status, mensagem, detalhes_json, data_hora
        FROM logs_api
        WHERE usuario = ?
        ORDER BY id ASC
        """,
        (usuario,),
    )
    logs = cursor.fetchall()
    conn.close()

    return [
        {
            "endpoint": row["endpoint"],
            "acao": row["acao"],
            "status": row["status"],
            "mensagem": row["mensagem"],
            "detalhes": json.loads(row["detalhes_json"]) if row["detalhes_json"] else None,
            "data_hora": row["data_hora"],
        }
        for row in logs
    ]


class SQLiteUserRepository(IUserRepository):
    def __init__(self):
        iniciar_banco_sqlite()

    def criar_usuario(
        self,
        email: str,
        senha_pura: str,
        nome: str | None = None,
        idade: int | str | None = None,
        foto_url: str | None = None,
        descricao: str | None = None,
        localizacao: str | None = None,
        cargo: str | None = None,
    ) -> bool:
        email = _normalizar_email_obrigatorio(email)
        nome = normalizar_nome_usuario(nome, email)

        if not email or not senha_pura:
            return False

        senha_hash = bcrypt.hashpw(senha_pura.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        conn = conectar()
        try:
            conn.execute(
                "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
                (nome, email, senha_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

        salvar_perfil_publico(
            usuario=email,
            nome=nome,
            idade=idade,
            foto_url=foto_url,
            descricao=descricao,
            localizacao=localizacao,
            cargo=cargo,
            origem="real",
            mock_customizado=False,
        )
        return True

    def buscar_usuario_por_email(self, email: str) -> dict | None:
        email = _normalizar_email_obrigatorio(email)
        if not email:
            return None

        conn = conectar()
        try:
            cursor = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
            linha = cursor.fetchone()
            return dict(linha) if linha else None
        finally:
            conn.close()

"""Conexão SQLite e migração automática dos CSVs legados para o banco.

Este módulo é o único responsável por "onde as coisas ficam no disco".
`app/storage.py` importa `db` e nunca toca em arquivo diretamente.
"""

import csv
import hashlib
import os
import secrets
import sqlite3
import sys
import threading
import uuid as uuid_lib

if getattr(sys, "frozen", False):
    # Executável empacotado (PyInstaller): __file__ aponta para a pasta
    # temporária de extração, que é apagada a cada execução. Os dados
    # precisam ficar ao lado do executável para persistir entre execuções.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "estoque.db")

# Caminhos/headers dos CSVs legados — usados só durante a migração automática
# de uma instalação anterior (baseada em CSV) para o banco.
PRODUTOS_CSV = os.path.join(DATA_DIR, "produtos.csv")
ENTRADAS_CSV = os.path.join(DATA_DIR, "entradas_estoque.csv")
SAIDAS_CSV = os.path.join(DATA_DIR, "saidas_estoque.csv")
CLIENTES_CSV = os.path.join(DATA_DIR, "clientes.csv")
USUARIOS_CSV = os.path.join(DATA_DIR, "usuarios.csv")

PRODUTOS_HEADERS = [
    "codigo_barras", "nome", "valor", "unidade_medida", "e_caixa", "quantidade_pacotes", "produto_relacionado",
]
ENTRADAS_HEADERS = ["data_hora", "codigo_barras", "nome", "quantidade", "usuario"]
SAIDAS_HEADERS = ["data_hora", "codigo_barras", "nome", "quantidade", "cliente", "data_entrega", "usuario"]
CLIENTES_HEADERS = ["id", "nome", "unidade"]
USUARIOS_HEADERS = ["usuario", "senha_hash", "salt"]

_USUARIOS_INICIAIS = [
    ("Jussara", "@porto498015"),
    ("Sarah", "S152489"),
    ("Pedro", "#200089pHB"),
]

SCHEMA_SQL = """
CREATE TABLE produtos (
    codigo_barras       TEXT PRIMARY KEY,
    nome                TEXT NOT NULL,
    valor               REAL NOT NULL DEFAULT 0,
    unidade_medida      TEXT NOT NULL DEFAULT 'g',
    e_caixa             INTEGER NOT NULL DEFAULT 0 CHECK (e_caixa IN (0, 1)),
    quantidade_pacotes  INTEGER,
    produto_relacionado TEXT REFERENCES produtos(codigo_barras) ON DELETE SET NULL
);

CREATE TABLE entradas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid          TEXT NOT NULL,
    data_hora     TEXT NOT NULL,
    codigo_barras TEXT NOT NULL,
    nome          TEXT NOT NULL,
    quantidade    INTEGER NOT NULL,
    usuario       TEXT NOT NULL,
    origem        TEXT NOT NULL DEFAULT '',
    sincronizado  INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_entradas_data_hora     ON entradas(data_hora);
CREATE INDEX idx_entradas_codigo_barras ON entradas(codigo_barras);
CREATE UNIQUE INDEX idx_entradas_uuid   ON entradas(uuid);

CREATE TABLE saidas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid          TEXT NOT NULL,
    data_hora     TEXT NOT NULL,
    codigo_barras TEXT NOT NULL,
    nome          TEXT NOT NULL,
    quantidade    INTEGER NOT NULL,
    cliente       TEXT NOT NULL DEFAULT '',
    data_entrega  TEXT NOT NULL DEFAULT '',
    usuario       TEXT NOT NULL,
    origem        TEXT NOT NULL DEFAULT '',
    sincronizado  INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_saidas_data_hora     ON saidas(data_hora);
CREATE INDEX idx_saidas_codigo_barras ON saidas(codigo_barras);
CREATE UNIQUE INDEX idx_saidas_uuid   ON saidas(uuid);

CREATE TABLE clientes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nome    TEXT NOT NULL,
    unidade TEXT NOT NULL DEFAULT ''
);

CREATE TABLE usuarios (
    usuario    TEXT PRIMARY KEY,
    senha_hash TEXT NOT NULL,
    salt       TEXT NOT NULL
);

PRAGMA user_version = 2;
"""

SCHEMA_VERSION_ATUAL = 2

_local = threading.local()


def hash_senha(senha, salt):
    return hashlib.sha256(f"{salt}{senha}".encode("utf-8")).hexdigest()


def _migrar_produtos_csv():
    """Adiciona colunas novas a um produtos.csv de uma versão anterior, preservando os dados."""
    if not os.path.exists(PRODUTOS_CSV):
        return
    with open(PRODUTOS_CSV, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), None)
    if header == PRODUTOS_HEADERS:
        return
    with open(PRODUTOS_CSV, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, restval=""))
    with open(PRODUTOS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRODUTOS_HEADERS)
        writer.writeheader()
        for linha in linhas:
            nova = {campo: linha.get(campo, "") for campo in PRODUTOS_HEADERS}
            if not nova["valor"] and linha.get("peso_gramas"):
                # Versões anteriores só tinham peso, sempre normalizado em gramas.
                nova["valor"] = linha["peso_gramas"]
                nova["unidade_medida"] = "g"
            writer.writerow(nova)


def _migrar_csv_movimento(path, headers):
    """Adiciona a coluna 'usuario' a um entradas/saidas CSV de versão anterior.

    Linhas gravadas antes da existência do login não têm autor conhecido, e
    recebem o marcador "desconhecido" em vez de ficarem em branco.
    """
    if not os.path.exists(path):
        return
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), None)
    if header == headers:
        return
    with open(path, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, restval=""))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for linha in linhas:
            nova = {campo: linha.get(campo, "") for campo in headers}
            if not nova.get("usuario"):
                nova["usuario"] = "desconhecido"
            writer.writerow(nova)


def _importar_produtos(conn):
    with open(PRODUTOS_CSV, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        valor_raw = (linha.get("valor") or "").strip()
        try:
            valor = float(valor_raw) if valor_raw else 0.0
        except ValueError:
            valor = 0.0
        qtd_raw = (linha.get("quantidade_pacotes") or "").strip()
        quantidade_pacotes = int(qtd_raw) if qtd_raw else None
        relacionado = (linha.get("produto_relacionado") or "").strip() or None
        conn.execute(
            "INSERT INTO produtos "
            "(codigo_barras, nome, valor, unidade_medida, e_caixa, quantidade_pacotes, produto_relacionado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                linha["codigo_barras"],
                linha["nome"],
                valor,
                linha.get("unidade_medida") or "g",
                1 if linha.get("e_caixa") == "sim" else 0,
                quantidade_pacotes,
                relacionado,
            ),
        )


def _importar_usuarios(conn):
    with open(USUARIOS_CSV, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, salt) VALUES (?, ?, ?)",
            (linha["usuario"], linha["senha_hash"], linha["salt"]),
        )


def _importar_movimento(conn, path, tabela, tem_cliente):
    with open(path, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        usuario = linha.get("usuario") or "desconhecido"
        if tem_cliente:
            conn.execute(
                f"INSERT INTO {tabela} "
                "(uuid, data_hora, codigo_barras, nome, quantidade, cliente, data_entrega, usuario) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid_lib.uuid4().hex, linha["data_hora"], linha["codigo_barras"], linha["nome"],
                    int(linha["quantidade"]), linha.get("cliente", ""), linha.get("data_entrega", ""), usuario,
                ),
            )
        else:
            conn.execute(
                f"INSERT INTO {tabela} (uuid, data_hora, codigo_barras, nome, quantidade, usuario) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (uuid_lib.uuid4().hex, linha["data_hora"], linha["codigo_barras"], linha["nome"],
                 int(linha["quantidade"]), usuario),
            )


def _importar_clientes(conn):
    with open(CLIENTES_CSV, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        conn.execute(
            "INSERT INTO clientes (id, nome, unidade) VALUES (?, ?, ?)",
            (int(linha["id"]), linha["nome"], linha.get("unidade", "")),
        )


def _seed_usuarios_iniciais(conn):
    for usuario, senha in _USUARIOS_INICIAIS:
        salt = secrets.token_hex(16)
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, salt) VALUES (?, ?, ?)",
            (usuario, hash_senha(senha, salt), salt),
        )


def _construir_banco_novo():
    """Cria data/estoque.db do zero, importando os CSVs legados que existirem.

    Constrói tudo em um arquivo temporário e só publica em DB_PATH via rename
    atômico ao final — se o processo morrer no meio do caminho, DB_PATH nunca
    chega a existir e a próxima execução recomeça do zero, com os CSVs
    originais ainda intactos (só viram .bak depois que o banco já está
    publicado com sucesso).
    """
    tmp_path = DB_PATH + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    csvs = {
        PRODUTOS_CSV: os.path.exists(PRODUTOS_CSV),
        USUARIOS_CSV: os.path.exists(USUARIOS_CSV),
        ENTRADAS_CSV: os.path.exists(ENTRADAS_CSV),
        SAIDAS_CSV: os.path.exists(SAIDAS_CSV),
        CLIENTES_CSV: os.path.exists(CLIENTES_CSV),
    }

    conn = sqlite3.connect(tmp_path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(SCHEMA_SQL)

        if csvs[PRODUTOS_CSV]:
            _migrar_produtos_csv()
            _importar_produtos(conn)
        if csvs[USUARIOS_CSV]:
            _importar_usuarios(conn)
        if csvs[ENTRADAS_CSV]:
            _migrar_csv_movimento(ENTRADAS_CSV, ENTRADAS_HEADERS)
            _importar_movimento(conn, ENTRADAS_CSV, "entradas", tem_cliente=False)
        if csvs[SAIDAS_CSV]:
            _migrar_csv_movimento(SAIDAS_CSV, SAIDAS_HEADERS)
            _importar_movimento(conn, SAIDAS_CSV, "saidas", tem_cliente=True)
        if csvs[CLIENTES_CSV]:
            _importar_clientes(conn)

        total_usuarios = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if total_usuarios == 0:
            _seed_usuarios_iniciais(conn)

        conn.commit()
    finally:
        conn.close()

    os.replace(tmp_path, DB_PATH)

    for caminho, existia in csvs.items():
        if existia:
            os.replace(caminho, caminho + ".bak")


def _migrar_v1_para_v2(conn):
    """Adiciona uuid/origem/sincronizado a entradas e saidas, suporte à
    sincronização entre máquinas (controle_estoque-qw3). Linhas existentes
    (todas gravadas nesta máquina antes da funcionalidade existir) recebem um
    uuid novo e ficam marcadas como já sincronizadas, já que são a fonte da
    verdade local — não há nada pendente de envio."""
    for tabela in ("entradas", "saidas"):
        colunas = {row["name"] for row in conn.execute(f"PRAGMA table_info({tabela})")}
        if "uuid" not in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN uuid TEXT")
        if "origem" not in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN origem TEXT NOT NULL DEFAULT ''")
        if "sincronizado" not in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN sincronizado INTEGER NOT NULL DEFAULT 1")
        for row in conn.execute(f"SELECT id FROM {tabela} WHERE uuid IS NULL OR uuid = ''"):
            conn.execute(f"UPDATE {tabela} SET uuid = ? WHERE id = ?", (uuid_lib.uuid4().hex, row["id"]))
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{tabela}_uuid ON {tabela}(uuid)")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION_ATUAL}")
    conn.commit()


def _migrar_schema(conn):
    versao = conn.execute("PRAGMA user_version").fetchone()[0]
    if versao < SCHEMA_VERSION_ATUAL:
        _migrar_v1_para_v2(conn)


def ensure_db():
    is_new = not os.path.exists(DB_PATH)
    os.makedirs(DATA_DIR, exist_ok=True)
    if is_new:
        _construir_banco_novo()


def get_connection():
    """Conexão SQLite own-per-thread: o servidor de sincronização (app/sync.py)
    atende cada requisição numa thread própria, e conexões sqlite3 só podem ser
    usadas na thread onde foram criadas."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")  # evita "database is locked" ao concorrer com o servidor de sync
        _migrar_schema(conn)
        _local.conn = conn
    return conn

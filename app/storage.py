"""Leitura e escrita dos dados da aplicação em um banco SQLite local (data/estoque.db)."""

import hmac
import secrets
import uuid as uuid_lib
from datetime import datetime

from app import db, sync_config


def ensure_files():
    db.ensure_db()


def _timestamp_atual():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def listar_usuarios():
    ensure_files()
    conn = db.get_connection()
    rows = conn.execute("SELECT usuario, senha_hash, salt, admin FROM usuarios WHERE deletado = 0").fetchall()
    return [dict(row) for row in rows]


def verificar_login(usuario, senha):
    """Retorna o nome de usuário canônico (como gravado no banco) em caso de
    sucesso, ou None se usuário/senha inválidos."""
    usuario_norm = (usuario or "").strip().lower()
    for u in listar_usuarios():
        if u["usuario"].strip().lower() == usuario_norm:
            calculado = db.hash_senha(senha, u["salt"])
            if hmac.compare_digest(calculado, u["senha_hash"]):
                return u["usuario"]
            return None
    return None


def usuario_e_admin(usuario):
    usuario_norm = (usuario or "").strip().lower()
    for u in listar_usuarios():
        if u["usuario"].strip().lower() == usuario_norm:
            return bool(u["admin"])
    return False


def _buscar_usuario(usuario):
    usuario_norm = (usuario or "").strip().lower()
    for u in listar_usuarios():
        if u["usuario"].strip().lower() == usuario_norm:
            return u
    return None


def _total_admins(excluir_usuario=None):
    excluir_norm = (excluir_usuario or "").strip().lower()
    return sum(
        1 for u in listar_usuarios()
        if u["admin"] and u["usuario"].strip().lower() != excluir_norm
    )


def _buscar_usuario_linha_bruta(usuario):
    """Busca a linha de usuarios por nome (normalizado), incluindo removidos
    (deletado=1) — usado por `criar_usuario` para decidir entre INSERT e
    UPDATE, já que 'usuario' é chave primária e um nome removido nesta
    máquina mas ainda não sincronizado continua ocupando a linha."""
    usuario_norm = (usuario or "").strip().lower()
    conn = db.get_connection()
    return conn.execute("SELECT usuario FROM usuarios WHERE lower(usuario) = ?", (usuario_norm,)).fetchone()


def criar_usuario(usuario, senha, admin=False):
    """Cria um novo usuário. Levanta ValueError se já houver um usuário ativo com esse nome."""
    ensure_files()
    usuario = (usuario or "").strip()
    if not usuario:
        raise ValueError("Informe o nome de usuário.")
    if not senha:
        raise ValueError("Informe a senha.")
    if _buscar_usuario(usuario):
        raise ValueError(f"Já existe um usuário chamado '{usuario}'.")
    salt = secrets.token_hex(16)
    senha_hash = db.hash_senha(senha, salt)
    agora = _timestamp_atual()
    conn = db.get_connection()
    existente = _buscar_usuario_linha_bruta(usuario)
    if existente:
        conn.execute(
            "UPDATE usuarios SET usuario = ?, senha_hash = ?, salt = ?, admin = ?, "
            "atualizado_em = ?, deletado = 0 WHERE usuario = ?",
            (usuario, senha_hash, salt, 1 if admin else 0, agora, existente["usuario"]),
        )
    else:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, salt, admin, atualizado_em, deletado) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (usuario, senha_hash, salt, 1 if admin else 0, agora),
        )
    conn.commit()


def atualizar_usuario(usuario_atual, novo_usuario=None, nova_senha=None, admin=None):
    """Atualiza nome/senha/admin de um usuário existente.

    Movimentações passadas (entradas/saidas.usuario) guardam o nome de quem
    agiu na hora, não uma referência viva ao usuário — renomear aqui não
    reescreve o histórico, de propósito, para preservar a auditoria original.
    """
    ensure_files()
    atual = _buscar_usuario(usuario_atual)
    if not atual:
        raise ValueError(f"Usuário '{usuario_atual}' não encontrado.")

    if admin is False and bool(atual["admin"]) and _total_admins(excluir_usuario=usuario_atual) == 0:
        raise ValueError("Não é possível remover o último administrador do sistema.")

    conn = db.get_connection()
    agora = _timestamp_atual()
    if novo_usuario is not None:
        novo_usuario = novo_usuario.strip()
        if not novo_usuario:
            raise ValueError("Informe o nome de usuário.")
        if novo_usuario.strip().lower() != usuario_atual.strip().lower() and _buscar_usuario(novo_usuario):
            raise ValueError(f"Já existe um usuário chamado '{novo_usuario}'.")
        conn.execute(
            "UPDATE usuarios SET usuario = ?, atualizado_em = ? WHERE usuario = ?",
            (novo_usuario, agora, atual["usuario"]),
        )
        atual_nome = novo_usuario
    else:
        atual_nome = atual["usuario"]

    if nova_senha:
        salt = secrets.token_hex(16)
        conn.execute(
            "UPDATE usuarios SET senha_hash = ?, salt = ?, atualizado_em = ? WHERE usuario = ?",
            (db.hash_senha(nova_senha, salt), salt, agora, atual_nome),
        )

    if admin is not None:
        conn.execute(
            "UPDATE usuarios SET admin = ?, atualizado_em = ? WHERE usuario = ?",
            (1 if admin else 0, agora, atual_nome),
        )

    conn.commit()


def remover_usuario(usuario):
    """Remove um usuário (soft-delete: marca `deletado` em vez de apagar a linha),
    para que a remoção em si se propague para as outras máquinas na próxima
    sincronização (ver `mesclar_usuarios`)."""
    ensure_files()
    atual = _buscar_usuario(usuario)
    if not atual:
        raise ValueError(f"Usuário '{usuario}' não encontrado.")
    if bool(atual["admin"]) and _total_admins(excluir_usuario=usuario) == 0:
        raise ValueError("Não é possível remover o último administrador do sistema.")
    conn = db.get_connection()
    conn.execute(
        "UPDATE usuarios SET deletado = 1, atualizado_em = ? WHERE usuario = ?",
        (_timestamp_atual(), atual["usuario"]),
    )
    conn.commit()


def _produto_row_to_dict(row):
    return {
        "codigo_barras": row["codigo_barras"],
        "nome": row["nome"],
        "valor": str(row["valor"]),
        "unidade_medida": row["unidade_medida"],
        "e_caixa": "sim" if row["e_caixa"] else "nao",
        "quantidade_pacotes": str(row["quantidade_pacotes"]) if row["quantidade_pacotes"] is not None else "",
        "produto_relacionado": row["produto_relacionado"] or "",
    }


def listar_produtos():
    ensure_files()
    conn = db.get_connection()
    rows = conn.execute("SELECT * FROM produtos").fetchall()
    return [_produto_row_to_dict(row) for row in rows]


def buscar_produto(codigo_barras):
    ensure_files()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM produtos WHERE codigo_barras = ?", (codigo_barras,)).fetchone()
    return _produto_row_to_dict(row) if row else None


def adicionar_produto(codigo_barras, nome, valor, unidade_medida, e_caixa, quantidade_pacotes, produto_relacionado=""):
    ensure_files()
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO produtos "
        "(codigo_barras, nome, valor, unidade_medida, e_caixa, quantidade_pacotes, produto_relacionado) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            codigo_barras,
            nome,
            float(valor),
            unidade_medida,
            1 if e_caixa else 0,
            int(quantidade_pacotes) if e_caixa and quantidade_pacotes not in (None, "") else None,
            produto_relacionado if e_caixa and produto_relacionado else None,
        ),
    )
    conn.commit()


def remover_produto(codigo_barras):
    ensure_files()
    conn = db.get_connection()
    cursor = conn.execute("DELETE FROM produtos WHERE codigo_barras = ?", (codigo_barras,))
    conn.commit()
    return cursor.rowcount > 0


def listar_clientes():
    ensure_files()
    conn = db.get_connection()
    rows = conn.execute("SELECT id, nome, unidade FROM clientes").fetchall()
    return [{"id": str(row["id"]), "nome": row["nome"], "unidade": row["unidade"]} for row in rows]


def nome_completo_cliente(cliente):
    """Nome de exibição do cliente, incluindo a unidade/localidade quando houver.

    Esse é o texto usado tanto para selecionar o cliente na saída de estoque
    quanto para filtrar por ele na visualização de estoque, garantindo que o
    mesmo cliente sempre apareça com o mesmo nome nos dois lugares.
    """
    unidade = (cliente.get("unidade") or "").strip()
    return f"{cliente['nome']} - {unidade}" if unidade else cliente["nome"]


def adicionar_cliente(nome, unidade=""):
    ensure_files()
    conn = db.get_connection()
    cursor = conn.execute("INSERT INTO clientes (nome, unidade) VALUES (?, ?)", (nome, unidade))
    conn.commit()
    return str(cursor.lastrowid)


def remover_cliente(cliente_id):
    ensure_files()
    conn = db.get_connection()
    cursor = conn.execute("DELETE FROM clientes WHERE id = ?", (int(cliente_id),))
    conn.commit()
    return cursor.rowcount > 0


def descrever_item_estoque(codigo_barras):
    """Descreve o produto identificado por um código lido na entrada/saída de estoque.

    Se o código for de uma caixa, o item descrito é a própria caixa (para que
    apareça como tal na tela), junto com os dados do produto relacionado e a
    quantidade de pacotes por caixa, usados depois para expandir a leitura em
    unidades do produto ao finalizar (ver `expandir_itens_pendentes`).
    Retorna None se o código não corresponder a nenhum produto cadastrado.
    """
    produto = buscar_produto(codigo_barras)
    if not produto:
        return None
    e_caixa = produto["e_caixa"] == "sim"
    item = {
        "codigo_barras": produto["codigo_barras"],
        "nome": produto["nome"],
        "e_caixa": e_caixa,
        "produto_relacionado_codigo": None,
        "produto_relacionado_nome": None,
        "quantidade_pacotes": None,
    }
    if e_caixa:
        relacionado = buscar_produto(produto["produto_relacionado"])
        if relacionado:
            item["produto_relacionado_codigo"] = relacionado["codigo_barras"]
            item["produto_relacionado_nome"] = relacionado["nome"]
        try:
            item["quantidade_pacotes"] = int(produto["quantidade_pacotes"])
        except (TypeError, ValueError):
            item["quantidade_pacotes"] = 0
    return item


def expandir_itens_pendentes(pendentes):
    """Converte os itens pendentes (produtos e caixas) na lista final a registrar.

    `pendentes` é um dict codigo_barras -> item (como montado nas telas de
    entrada/saída, com base em `descrever_item_estoque`). Uma caixa é expandida
    para o produto relacionado, multiplicando a quantidade de caixas lidas pela
    quantidade de pacotes por caixa; quantidades do mesmo produto final são
    somadas quando aparecem mais de uma vez (ex.: caixa + produto avulso).
    """
    agregados = {}
    for item in pendentes.values():
        if item["e_caixa"]:
            codigo = item["produto_relacionado_codigo"]
            nome = item["produto_relacionado_nome"]
            quantidade = item["quantidade"] * item["quantidade_pacotes"]
        else:
            codigo = item["codigo_barras"]
            nome = item["nome"]
            quantidade = item["quantidade"]
        registro = agregados.setdefault(codigo, {"codigo_barras": codigo, "nome": nome, "quantidade": 0})
        registro["quantidade"] += quantidade
    return list(agregados.values())


def resetar_estoque():
    """Apaga todo o histórico de entradas e saídas de estoque, mantendo os produtos cadastrados."""
    ensure_files()
    conn = db.get_connection()
    conn.execute("DELETE FROM entradas")
    conn.execute("DELETE FROM saidas")
    conn.commit()


def registrar_entrada(itens, usuario):
    """itens: lista de dicts com codigo_barras, nome, quantidade."""
    ensure_files()
    conn = db.get_connection()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    origem = sync_config.nome_desta_maquina()
    sincronizado = 0 if sync_config.carregar()["papel"] == sync_config.PAPEL_SECUNDARIA else 1
    for item in itens:
        conn.execute(
            "INSERT INTO entradas "
            "(uuid, data_hora, codigo_barras, nome, quantidade, usuario, origem, sincronizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid_lib.uuid4().hex, agora, item["codigo_barras"], item["nome"], item["quantidade"],
             usuario, origem, sincronizado),
        )
    conn.commit()


def registrar_saida(itens, cliente, data_entrega, usuario):
    """itens: lista de dicts com codigo_barras, nome, quantidade."""
    ensure_files()
    conn = db.get_connection()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    origem = sync_config.nome_desta_maquina()
    sincronizado = 0 if sync_config.carregar()["papel"] == sync_config.PAPEL_SECUNDARIA else 1
    for item in itens:
        conn.execute(
            "INSERT INTO saidas "
            "(uuid, data_hora, codigo_barras, nome, quantidade, cliente, data_entrega, usuario, origem, sincronizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid_lib.uuid4().hex, agora, item["codigo_barras"], item["nome"], item["quantidade"],
             cliente, data_entrega, usuario, origem, sincronizado),
        )
    conn.commit()


def listar_entradas():
    ensure_files()
    conn = db.get_connection()
    rows = conn.execute("SELECT data_hora, codigo_barras, nome, quantidade, usuario FROM entradas").fetchall()
    return [
        {
            "data_hora": row["data_hora"],
            "codigo_barras": row["codigo_barras"],
            "nome": row["nome"],
            "quantidade": str(row["quantidade"]),
            "usuario": row["usuario"],
        }
        for row in rows
    ]


def listar_saidas():
    ensure_files()
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT data_hora, codigo_barras, nome, quantidade, cliente, data_entrega, usuario FROM saidas"
    ).fetchall()
    return [
        {
            "data_hora": row["data_hora"],
            "codigo_barras": row["codigo_barras"],
            "nome": row["nome"],
            "quantidade": str(row["quantidade"]),
            "cliente": row["cliente"],
            "data_entrega": row["data_entrega"],
            "usuario": row["usuario"],
        }
        for row in rows
    ]


def listar_movimentos():
    """Une entradas e saídas em uma única lista, mais recente primeiro."""
    movimentos = []
    for item in listar_entradas():
        movimentos.append({
            "data_hora": item["data_hora"],
            "tipo": "entrada",
            "codigo_barras": item["codigo_barras"],
            "nome": item["nome"],
            "quantidade": item["quantidade"],
            "cliente": "",
            "data_entrega": "",
            "usuario": item.get("usuario", ""),
        })
    for item in listar_saidas():
        movimentos.append({
            "data_hora": item["data_hora"],
            "tipo": "saida",
            "codigo_barras": item["codigo_barras"],
            "nome": item["nome"],
            "quantidade": item["quantidade"],
            "cliente": item["cliente"],
            "data_entrega": item["data_entrega"],
            "usuario": item.get("usuario", ""),
        })
    movimentos.sort(key=lambda m: m["data_hora"], reverse=True)
    return movimentos


def calcular_quantidades_reais():
    """Quantidade atual em estoque por produto: soma das entradas menos soma das saídas."""
    saldo = {}
    for item in listar_entradas():
        codigo = item["codigo_barras"]
        registro = saldo.setdefault(codigo, {"nome": item["nome"], "quantidade": 0})
        registro["quantidade"] += int(item["quantidade"])
    for item in listar_saidas():
        codigo = item["codigo_barras"]
        registro = saldo.setdefault(codigo, {"nome": item["nome"], "quantidade": 0})
        registro["quantidade"] -= int(item["quantidade"])
    resultado = [
        {"codigo_barras": codigo, "nome": dados["nome"], "quantidade": dados["quantidade"]}
        for codigo, dados in saldo.items()
    ]
    resultado.sort(key=lambda r: r["nome"].lower())
    return resultado


# --- Protocolo de sincronização entre máquinas (ver app/sync.py) ---------

def _produto_row_to_sync_dict(row):
    return {
        "codigo_barras": row["codigo_barras"],
        "nome": row["nome"],
        "valor": row["valor"],
        "unidade_medida": row["unidade_medida"],
        "e_caixa": row["e_caixa"],
        "quantidade_pacotes": row["quantidade_pacotes"],
        "produto_relacionado": row["produto_relacionado"],
    }


def _entrada_row_to_sync_dict(row):
    return {
        "uuid": row["uuid"],
        "data_hora": row["data_hora"],
        "codigo_barras": row["codigo_barras"],
        "nome": row["nome"],
        "quantidade": row["quantidade"],
        "usuario": row["usuario"],
        "origem": row["origem"],
    }


def _saida_row_to_sync_dict(row):
    return {
        "uuid": row["uuid"],
        "data_hora": row["data_hora"],
        "codigo_barras": row["codigo_barras"],
        "nome": row["nome"],
        "quantidade": row["quantidade"],
        "cliente": row["cliente"],
        "data_entrega": row["data_entrega"],
        "usuario": row["usuario"],
        "origem": row["origem"],
    }


def _usuario_row_to_sync_dict(row):
    return {
        "usuario": row["usuario"],
        "senha_hash": row["senha_hash"],
        "salt": row["salt"],
        "admin": row["admin"],
        "atualizado_em": row["atualizado_em"],
        "deletado": row["deletado"],
    }


def dados_para_sincronizacao():
    """Todo o conteúdo do banco no formato do protocolo de sincronização (lado principal, GET /sync/full).

    Usuarios incluem removidos (deletado=1) e o timestamp de atualização —
    a secundária substitui sua tabela inteira por este retorno (ver
    `aplicar_dados_sincronizados`), e precisa desses dois campos para poder
    reenviar esse mesmo estado num push futuro (ver `movimentos_pendentes` e
    `mesclar_usuarios`).
    """
    ensure_files()
    conn = db.get_connection()
    return {
        "produtos": [_produto_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM produtos")],
        "clientes": [dict(r) for r in conn.execute("SELECT id, nome, unidade FROM clientes")],
        "usuarios": [_usuario_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM usuarios")],
        "entradas": [_entrada_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM entradas")],
        "saidas": [_saida_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM saidas")],
    }


def movimentos_pendentes():
    """Entradas/saídas criadas localmente ainda não enviadas à principal, e o
    estado local completo de usuarios (lado secundária, antes do POST /sync/push).

    Usuarios vai inteiro (não só os "pendentes") porque a tabela é pequena e
    mutável (criar/editar/remover, não só inserir) — a principal mescla essa
    lista com a dela mantendo, por usuário, a versão com atualizado_em mais
    recente (ver `mesclar_usuarios`). É assim que um usuário cadastrado numa
    secundária deixa de ser apagado no sync seguinte.
    """
    ensure_files()
    conn = db.get_connection()
    return {
        "entradas": [
            _entrada_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM entradas WHERE sincronizado = 0")
        ],
        "saidas": [
            _saida_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM saidas WHERE sincronizado = 0")
        ],
        "usuarios": [_usuario_row_to_sync_dict(r) for r in conn.execute("SELECT * FROM usuarios")],
    }


def mesclar_usuarios(usuarios_recebidos):
    """Mescla usuarios recebidos no push de uma máquina secundária (lado
    principal, POST /sync/push).

    Para cada usuário recebido, mantém a versão com atualizado_em mais
    recente entre a local e a recebida (last-write-wins por usuário,
    comparado por nome normalizado). Cobre criação, edição e remoção
    (soft-delete) feitas na secundária — a versão mesclada resultante é o que
    a principal devolve depois em GET /sync/full, propagando para as demais
    máquinas no sync delas.
    """
    ensure_files()
    conn = db.get_connection()
    for item in usuarios_recebidos:
        nome_norm = (item.get("usuario") or "").strip().lower()
        if not nome_norm:
            continue
        atual = conn.execute(
            "SELECT usuario, atualizado_em FROM usuarios WHERE lower(usuario) = ?", (nome_norm,)
        ).fetchone()
        if atual and (atual["atualizado_em"] or "") >= (item.get("atualizado_em") or ""):
            continue
        if atual:
            conn.execute("DELETE FROM usuarios WHERE usuario = ?", (atual["usuario"],))
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, salt, admin, atualizado_em, deletado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                item["usuario"], item["senha_hash"], item["salt"], 1 if item.get("admin") else 0,
                item.get("atualizado_em") or "", 1 if item.get("deletado") else 0,
            ),
        )
    conn.commit()


def registrar_movimentos_recebidos(entradas, saidas):
    """Insere movimentações recebidas de uma máquina secundária (lado principal, POST /sync/push).

    Idempotente: uma movimentação com um uuid já conhecido é ignorada — a
    máquina secundária reenvia tudo que ainda não confirmou como recebido,
    então o mesmo lote pode chegar mais de uma vez (ex.: se a conexão cair
    depois do envio mas antes da secundária terminar de processar a resposta).
    """
    ensure_files()
    conn = db.get_connection()
    antes_entradas = conn.execute("SELECT COUNT(*) FROM entradas").fetchone()[0]
    antes_saidas = conn.execute("SELECT COUNT(*) FROM saidas").fetchone()[0]
    for item in entradas:
        conn.execute(
            "INSERT OR IGNORE INTO entradas "
            "(uuid, data_hora, codigo_barras, nome, quantidade, usuario, origem, sincronizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            (item["uuid"], item["data_hora"], item["codigo_barras"], item["nome"],
             int(item["quantidade"]), item["usuario"], item.get("origem", "")),
        )
    for item in saidas:
        conn.execute(
            "INSERT OR IGNORE INTO saidas "
            "(uuid, data_hora, codigo_barras, nome, quantidade, cliente, data_entrega, usuario, origem, sincronizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (item["uuid"], item["data_hora"], item["codigo_barras"], item["nome"], int(item["quantidade"]),
             item.get("cliente", ""), item.get("data_entrega", ""), item["usuario"], item.get("origem", "")),
        )
    conn.commit()
    depois_entradas = conn.execute("SELECT COUNT(*) FROM entradas").fetchone()[0]
    depois_saidas = conn.execute("SELECT COUNT(*) FROM saidas").fetchone()[0]
    return {
        "entradas_recebidas": depois_entradas - antes_entradas,
        "saidas_recebidas": depois_saidas - antes_saidas,
    }


def aplicar_dados_sincronizados(dados):
    """Substitui produtos/clientes/usuarios/entradas/saidas locais pelos dados vindos da máquina
    principal (lado secundária, depois do GET /sync/full).

    A substituição é total nas 5 tabelas. Isso só é seguro porque é sempre
    chamada depois que `movimentos_pendentes()` já foi enviado com sucesso à
    principal (ver `sync.sincronizar`): tudo que existia só localmente já está
    representado no retorno da principal, então não há risco de perder
    movimentações criadas nesta máquina.
    """
    ensure_files()
    conn = db.get_connection()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("DELETE FROM produtos")
        for p in dados.get("produtos", []):
            conn.execute(
                "INSERT INTO produtos "
                "(codigo_barras, nome, valor, unidade_medida, e_caixa, quantidade_pacotes, produto_relacionado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["codigo_barras"], p["nome"], p["valor"], p["unidade_medida"], p["e_caixa"],
                 p["quantidade_pacotes"], p["produto_relacionado"]),
            )

        conn.execute("DELETE FROM clientes")
        for c in dados.get("clientes", []):
            conn.execute(
                "INSERT INTO clientes (id, nome, unidade) VALUES (?, ?, ?)", (c["id"], c["nome"], c["unidade"])
            )

        conn.execute("DELETE FROM usuarios")
        for u in dados.get("usuarios", []):
            conn.execute(
                "INSERT INTO usuarios (usuario, senha_hash, salt, admin, atualizado_em, deletado) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    u["usuario"], u["senha_hash"], u["salt"], 1 if u.get("admin") else 0,
                    u.get("atualizado_em") or "", 1 if u.get("deletado") else 0,
                ),
            )

        conn.execute("DELETE FROM entradas")
        for e in dados.get("entradas", []):
            conn.execute(
                "INSERT INTO entradas (uuid, data_hora, codigo_barras, nome, quantidade, usuario, origem, sincronizado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                (e["uuid"], e["data_hora"], e["codigo_barras"], e["nome"], e["quantidade"], e["usuario"],
                 e.get("origem", "")),
            )

        conn.execute("DELETE FROM saidas")
        for s in dados.get("saidas", []):
            conn.execute(
                "INSERT INTO saidas "
                "(uuid, data_hora, codigo_barras, nome, quantidade, cliente, data_entrega, usuario, origem, sincronizado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (s["uuid"], s["data_hora"], s["codigo_barras"], s["nome"], s["quantidade"], s["cliente"],
                 s["data_entrega"], s["usuario"], s.get("origem", "")),
            )

        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")

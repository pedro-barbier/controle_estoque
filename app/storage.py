"""Leitura e escrita dos dados da aplicação em arquivos CSV separados."""

import csv
import hashlib
import hmac
import os
import secrets
import sys
from datetime import datetime

if getattr(sys, "frozen", False):
    # Executável empacotado (PyInstaller): __file__ aponta para a pasta
    # temporária de extração, que é apagada a cada execução. Os dados
    # precisam ficar ao lado do executável para persistir entre execuções.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")

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


def _ensure_csv(path, headers):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)


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


def _hash_senha(senha, salt):
    return hashlib.sha256(f"{salt}{senha}".encode("utf-8")).hexdigest()


def _seed_usuarios_iniciais():
    with open(USUARIOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for usuario, senha in _USUARIOS_INICIAIS:
            salt = secrets.token_hex(16)
            writer.writerow([usuario, _hash_senha(senha, salt), salt])


def ensure_files():
    _ensure_csv(PRODUTOS_CSV, PRODUTOS_HEADERS)
    _migrar_produtos_csv()

    usuarios_novo = not os.path.exists(USUARIOS_CSV)
    _ensure_csv(USUARIOS_CSV, USUARIOS_HEADERS)
    if usuarios_novo:
        _seed_usuarios_iniciais()

    _ensure_csv(ENTRADAS_CSV, ENTRADAS_HEADERS)
    _migrar_csv_movimento(ENTRADAS_CSV, ENTRADAS_HEADERS)
    _ensure_csv(SAIDAS_CSV, SAIDAS_HEADERS)
    _migrar_csv_movimento(SAIDAS_CSV, SAIDAS_HEADERS)
    _ensure_csv(CLIENTES_CSV, CLIENTES_HEADERS)


def listar_usuarios():
    ensure_files()
    with open(USUARIOS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verificar_login(usuario, senha):
    """Retorna o nome de usuário canônico (como gravado no CSV) em caso de
    sucesso, ou None se usuário/senha inválidos."""
    usuario_norm = (usuario or "").strip().lower()
    for u in listar_usuarios():
        if u["usuario"].strip().lower() == usuario_norm:
            calculado = _hash_senha(senha, u["salt"])
            if hmac.compare_digest(calculado, u["senha_hash"]):
                return u["usuario"]
            return None
    return None


def listar_produtos():
    ensure_files()
    with open(PRODUTOS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def buscar_produto(codigo_barras):
    for produto in listar_produtos():
        if produto["codigo_barras"] == codigo_barras:
            return produto
    return None


def adicionar_produto(codigo_barras, nome, valor, unidade_medida, e_caixa, quantidade_pacotes, produto_relacionado=""):
    ensure_files()
    with open(PRODUTOS_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            codigo_barras,
            nome,
            valor,
            unidade_medida,
            "sim" if e_caixa else "nao",
            quantidade_pacotes if e_caixa else "",
            produto_relacionado if e_caixa else "",
        ])


def remover_produto(codigo_barras):
    produtos = listar_produtos()
    restantes = [p for p in produtos if p["codigo_barras"] != codigo_barras]
    if len(restantes) == len(produtos):
        return False
    with open(PRODUTOS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRODUTOS_HEADERS)
        writer.writeheader()
        writer.writerows(restantes)
    return True


def listar_clientes():
    ensure_files()
    with open(CLIENTES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
    clientes = listar_clientes()
    proximo_id = str(max((int(c["id"]) for c in clientes), default=0) + 1)
    with open(CLIENTES_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([proximo_id, nome, unidade])
    return proximo_id


def remover_cliente(cliente_id):
    clientes = listar_clientes()
    restantes = [c for c in clientes if c["id"] != cliente_id]
    if len(restantes) == len(clientes):
        return False
    with open(CLIENTES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CLIENTES_HEADERS)
        writer.writeheader()
        writer.writerows(restantes)
    return True


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
    with open(ENTRADAS_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(ENTRADAS_HEADERS)
    with open(SAIDAS_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(SAIDAS_HEADERS)


def registrar_entrada(itens, usuario):
    """itens: lista de dicts com codigo_barras, nome, quantidade."""
    ensure_files()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ENTRADAS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in itens:
            writer.writerow([agora, item["codigo_barras"], item["nome"], item["quantidade"], usuario])


def registrar_saida(itens, cliente, data_entrega, usuario):
    """itens: lista de dicts com codigo_barras, nome, quantidade."""
    ensure_files()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SAIDAS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in itens:
            writer.writerow([
                agora, item["codigo_barras"], item["nome"], item["quantidade"], cliente, data_entrega, usuario
            ])


def listar_entradas():
    ensure_files()
    with open(ENTRADAS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def listar_saidas():
    ensure_files()
    with open(SAIDAS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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

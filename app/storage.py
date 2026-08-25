"""Leitura e escrita dos dados da aplicação em arquivos CSV separados."""

import csv
import os
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

PRODUTOS_HEADERS = [
    "codigo_barras", "nome", "peso_gramas", "e_caixa", "quantidade_pacotes", "produto_relacionado",
]
ENTRADAS_HEADERS = ["data_hora", "codigo_barras", "nome", "quantidade"]
SAIDAS_HEADERS = ["data_hora", "codigo_barras", "nome", "quantidade", "cliente", "data_entrega"]


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
            writer.writerow({campo: linha.get(campo, "") for campo in PRODUTOS_HEADERS})


def ensure_files():
    _ensure_csv(PRODUTOS_CSV, PRODUTOS_HEADERS)
    _migrar_produtos_csv()
    _ensure_csv(ENTRADAS_CSV, ENTRADAS_HEADERS)
    _ensure_csv(SAIDAS_CSV, SAIDAS_HEADERS)


def listar_produtos():
    ensure_files()
    with open(PRODUTOS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def buscar_produto(codigo_barras):
    for produto in listar_produtos():
        if produto["codigo_barras"] == codigo_barras:
            return produto
    return None


def adicionar_produto(codigo_barras, nome, peso_gramas, e_caixa, quantidade_pacotes, produto_relacionado=""):
    ensure_files()
    with open(PRODUTOS_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            codigo_barras,
            nome,
            peso_gramas,
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


def resolver_leitura_estoque(codigo_barras):
    """Resolve um código lido para o produto e a quantidade a aplicar no estoque.

    Se o código for de uma caixa, resolve para o produto relacionado com a
    quantidade de pacotes cadastrada na caixa (em vez da caixa em si).
    Retorna None se o produto (ou o produto relacionado da caixa) não existir.
    """
    produto = buscar_produto(codigo_barras)
    if not produto:
        return None
    if produto["e_caixa"] == "sim":
        relacionado = buscar_produto(produto["produto_relacionado"])
        if not relacionado:
            return None
        try:
            quantidade = int(produto["quantidade_pacotes"])
        except (TypeError, ValueError):
            quantidade = 0
        return {
            "codigo_barras": relacionado["codigo_barras"],
            "nome": relacionado["nome"],
            "quantidade": quantidade,
        }
    return {
        "codigo_barras": produto["codigo_barras"],
        "nome": produto["nome"],
        "quantidade": 1,
    }


def registrar_entrada(itens):
    """itens: lista de dicts com codigo_barras, nome, quantidade."""
    ensure_files()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ENTRADAS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in itens:
            writer.writerow([agora, item["codigo_barras"], item["nome"], item["quantidade"]])


def registrar_saida(itens, cliente, data_entrega):
    """itens: lista de dicts com codigo_barras, nome, quantidade."""
    ensure_files()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SAIDAS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in itens:
            writer.writerow([
                agora, item["codigo_barras"], item["nome"], item["quantidade"], cliente, data_entrega
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

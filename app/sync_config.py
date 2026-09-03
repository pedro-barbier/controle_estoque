"""Configuração de sincronização entre máquinas (papel, IP da principal, nome desta máquina).

Fica fora do banco de dados (arquivo JSON separado, `data/sync_config.json`)
de propósito: é uma configuração específica desta instalação/máquina, que não
pode ser sobrescrita quando os dados são substituídos por uma sincronização
(ver `storage.aplicar_dados_sincronizados`).
"""

import json
import os
import socket

from app import db

CONFIG_PATH = os.path.join(db.DATA_DIR, "sync_config.json")

PAPEL_ISOLADO = "isolado"
PAPEL_PRINCIPAL = "principal"
PAPEL_SECUNDARIA = "secundaria"

PADRAO = {
    "papel": PAPEL_ISOLADO,
    "porta_servidor": 8765,
    "principal_ip": "",
    "principal_porta": 8765,
    "nome_maquina": "",
}


def carregar():
    if not os.path.exists(CONFIG_PATH):
        return dict(PADRAO)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            dados = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(PADRAO)
    config = dict(PADRAO)
    config.update({chave: valor for chave, valor in dados.items() if chave in PADRAO})
    return config


def salvar(config):
    os.makedirs(db.DATA_DIR, exist_ok=True)
    atual = dict(PADRAO)
    atual.update({chave: valor for chave, valor in config.items() if chave in PADRAO})
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)


def nome_desta_maquina():
    nome = carregar()["nome_maquina"].strip()
    return nome or socket.gethostname()

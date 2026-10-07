"""Arquivos embutidos no programa (hoje só o ícone), lidos em tempo de execução."""

import os
import sys

from PIL import Image

if getattr(sys, "frozen", False):
    # Executável empacotado (PyInstaller): arquivos passados com --add-data
    # são extraídos para a pasta temporária sys._MEIPASS. Diferente de
    # db.BASE_DIR, que aponta para o lado do executável (onde fica a pasta data).
    _PASTA_RECURSOS = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    _PASTA_RECURSOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICONE = "icon.png"

_cache_icones = {}


def caminho_recurso(nome):
    return os.path.join(_PASTA_RECURSOS, nome)


def carregar_icone(tamanho):
    """Ícone do programa (icon.png) reduzido para `tamanho` x `tamanho` px, ou
    None se o arquivo não puder ser lido — quem chama cai no ícone padrão."""
    if tamanho not in _cache_icones:
        try:
            with Image.open(caminho_recurso(ICONE)) as original:
                imagem = original.convert("RGBA")
            imagem.thumbnail((tamanho, tamanho), Image.LANCZOS)
            _cache_icones[tamanho] = imagem
        except OSError:
            return None
    return _cache_icones[tamanho]

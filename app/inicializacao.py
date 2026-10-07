"""Opção "Iniciar com o Windows": abre o programa já escondido na bandeja
quando o usuário entra no Windows — útil principalmente na máquina principal,
para o servidor de sincronização estar sempre no ar depois de reiniciar o PC.

Usa a chave Run do registro do usuário atual, que é a própria fonte da
verdade (nada é guardado em sync_config.json). Só faz sentido no executável
empacotado: em desenvolvimento não há um .exe para apontar.
"""

import sys

_CHAVE = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NOME = "ControleEstoqueCafe"


def disponivel():
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def _comando():
    return f'"{sys.executable}" --bandeja'


def esta_ativo():
    if not disponivel():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE) as chave:
            valor, _ = winreg.QueryValueEx(chave, _NOME)
    except OSError:
        return False
    return valor == _comando()


def definir(ativo):
    if not disponivel():
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE, 0, winreg.KEY_SET_VALUE) as chave:
        if ativo:
            winreg.SetValueEx(chave, _NOME, 0, winreg.REG_SZ, _comando())
        else:
            try:
                winreg.DeleteValue(chave, _NOME)
            except FileNotFoundError:
                pass

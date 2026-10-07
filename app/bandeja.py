"""Ícone do programa na bandeja do sistema (perto do relógio), que mantém o
app acessível depois que a janela é fechada (ver App.on_fechar_janela em main.py).

Os callbacks do pystray rodam na thread do ícone, e Tkinter não é
thread-safe — por isso o menu só coloca comandos ("abrir"/"sair") numa fila,
que a janela consome na thread principal (App._processar_fila).
"""

import sys
import threading

from app import recursos

_icone = None


def _backend_confiavel(pystray):
    """No Windows o ícone sempre aparece. No Linux (só desenvolvimento) o
    backend xorg (XEmbed) não aparece em bandejas Wayland (ex.: waybar), e o
    app ficaria escondido sem ícone para reabrir — só aceita o appindicator."""
    if sys.platform == "win32":
        return True
    return pystray.Icon.__module__ in ("pystray._appindicator", "pystray._darwin")


def iniciar(fila, tooltip):
    """Mostra o ícone na bandeja. Retorna False se não for possível (pystray
    ausente ou sem bandeja confiável); nesse caso fechar a janela encerra o
    programa, como antes."""
    global _icone
    try:
        import pystray
    except Exception:
        return False
    if not _backend_confiavel(pystray):
        return False

    imagem = recursos.carregar_icone(64)
    if imagem is None:
        from PIL import Image
        imagem = Image.new("RGBA", (64, 64), (0, 47, 63, 255))

    menu = pystray.Menu(
        pystray.MenuItem("Abrir", lambda icon, item: fila.put("abrir"), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair (encerrar completamente)", lambda icon, item: fila.put("sair")),
    )
    try:
        _icone = pystray.Icon("ControleEstoqueCafe", imagem, tooltip, menu)
        threading.Thread(target=_icone.run, daemon=True).start()
    except Exception:
        _icone = None
        return False
    return True


def notificar(texto):
    if _icone is None or not getattr(_icone, "HAS_NOTIFICATION", False):
        return
    try:
        _icone.notify(texto, "Controle de Estoque")
    except Exception:
        pass


def parar():
    global _icone
    if _icone is not None:
        try:
            _icone.stop()
        except Exception:
            pass
        _icone = None

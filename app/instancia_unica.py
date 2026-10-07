"""Garante um único processo do programa por máquina.

Como fechar a janela não encerra mais o programa (ele fica na bandeja), abrir
o atalho de novo criaria um segundo processo — na principal, o servidor de
sincronização falharia por porta ocupada, e dois processos mexeriam no mesmo
banco. A primeira instância escuta numa porta local (só 127.0.0.1, nada é
exposto na rede); uma segunda instância apenas avisa a primeira para mostrar a
janela e encerra.
"""

import socket
import threading

PORTA = 47651
_MENSAGEM_ABRIR = b"abrir"

_servidor = None


def tentar_ser_primeira(fila):
    """Retorna True se este é o primeiro processo (e passa a escutar pedidos de
    "abrir", colocados em `fila`). Retorna False se já há outro rodando — nesse
    caso o outro já foi avisado para mostrar a janela."""
    global _servidor
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", PORTA))
    except OSError:
        sock.close()
        _avisar_instancia_existente()
        return False
    sock.listen(5)
    _servidor = sock

    def _escutar():
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return  # socket fechado em liberar()
            with conn:
                try:
                    if conn.recv(16) == _MENSAGEM_ABRIR:
                        fila.put("abrir")
                except OSError:
                    pass

    threading.Thread(target=_escutar, daemon=True).start()
    return True


def _avisar_instancia_existente():
    try:
        with socket.create_connection(("127.0.0.1", PORTA), timeout=2) as conn:
            conn.sendall(_MENSAGEM_ABRIR)
    except OSError:
        pass


def liberar():
    global _servidor
    if _servidor is not None:
        _servidor.close()
        _servidor = None

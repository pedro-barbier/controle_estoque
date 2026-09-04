"""Sincronização de dados entre máquinas na rede local (wifi).

A máquina "principal" roda um pequeno servidor HTTP (só biblioteca padrão,
sem dependências novas) que expõe o banco inteiro para leitura e recebe
movimentações novas criadas nas demais máquinas. As máquinas "secundárias"
falam com esse servidor pelo IP da principal na rede local.

Feito assim (servidor HTTP) em vez de apontar todas as máquinas para o mesmo
arquivo estoque.db numa pasta de rede compartilhada porque SQLite não garante
funcionamento correto sobre compartilhamento de rede (SMB) — o lock de
arquivo pela rede é uma fonte conhecida de corrupção de banco quando um
processo escreve enquanto outros leem, que é exatamente esse cenário.

Pensado para uma rede local confiável (wifi da loja); não há autenticação
entre as máquinas nem HTTPS.
"""

import json
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app import storage

TIMEOUT_SEGUNDOS = 5

_servidor = None
_ultimo_resultado = {"quando": None, "ok": None, "mensagem": ""}


class ErroSincronizacao(Exception):
    """Levantado quando não foi possível falar com a máquina principal."""


# --- Lado principal: servidor -------------------------------------------

class _SyncHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silencia o log padrão do http.server no console

    def _responder_json(self, status, dados):
        corpo = json.dumps(dados).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/sync/full":
            self._responder_json(200, storage.dados_para_sincronizacao())
        else:
            self._responder_json(404, {"erro": "não encontrado"})

    def do_POST(self):
        if self.path != "/sync/push":
            self._responder_json(404, {"erro": "não encontrado"})
            return
        tamanho = int(self.headers.get("Content-Length", 0) or 0)
        corpo = self.rfile.read(tamanho) if tamanho else b"{}"
        try:
            dados = json.loads(corpo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._responder_json(400, {"erro": "corpo inválido"})
            return
        storage.mesclar_usuarios(dados.get("usuarios", []))
        resultado = storage.registrar_movimentos_recebidos(dados.get("entradas", []), dados.get("saidas", []))
        self._responder_json(200, resultado)


def iniciar_servidor(porta):
    """Inicia o servidor de sincronização em background. Chamar só na máquina principal."""
    global _servidor
    if _servidor is not None:
        return
    _servidor = ThreadingHTTPServer(("0.0.0.0", porta), _SyncHandler)
    threading.Thread(target=_servidor.serve_forever, daemon=True).start()


def obter_ip_local():
    """Melhor esforço para descobrir o IP desta máquina na rede local (exibido na tela de configuração)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "desconhecido"
    finally:
        s.close()


# --- Lado secundária: cliente --------------------------------------------

def _requisicao_json(url, dados=None):
    corpo = json.dumps(dados).encode("utf-8") if dados is not None else None
    headers = {"Content-Type": "application/json; charset=utf-8"} if corpo is not None else {}
    req = Request(url, data=corpo, method="POST" if corpo is not None else "GET", headers=headers)
    try:
        with urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, ConnectionError, OSError) as exc:
        raise ErroSincronizacao(f"Não foi possível conectar à máquina principal ({exc}).") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise ErroSincronizacao("Resposta inválida da máquina principal.") from exc


def sincronizar(ip, porta):
    """Envia as movimentações locais pendentes e busca os dados atualizados da máquina principal.

    Levanta ErroSincronizacao se a principal estiver inacessível — nesse caso
    os dados locais não são alterados (o app continua funcionando offline com
    o que já tinha). Retorna um resumo do resultado em caso de sucesso.
    """
    if not ip:
        raise ErroSincronizacao("Nenhum IP de máquina principal configurado.")
    base = f"http://{ip}:{porta}"
    pendentes = storage.movimentos_pendentes()
    envio = _requisicao_json(f"{base}/sync/push", dados=pendentes)
    dados_completos = _requisicao_json(f"{base}/sync/full")
    storage.aplicar_dados_sincronizados(dados_completos)
    return {
        "entradas_enviadas": envio.get("entradas_recebidas", 0),
        "saidas_enviadas": envio.get("saidas_recebidas", 0),
        "total_produtos": len(dados_completos.get("produtos", [])),
        "total_entradas": len(dados_completos.get("entradas", [])),
        "total_saidas": len(dados_completos.get("saidas", [])),
    }


def status_atual():
    return dict(_ultimo_resultado)


def sincronizar_e_registrar(ip, porta):
    """Como `sincronizar`, mas também guarda o resultado (para exibir na tela principal)."""
    try:
        resumo = sincronizar(ip, porta)
        _ultimo_resultado.update(quando=datetime.now(), ok=True, mensagem="Sincronizado com sucesso.")
        return resumo
    except ErroSincronizacao as exc:
        _ultimo_resultado.update(quando=datetime.now(), ok=False, mensagem=str(exc))
        raise

"""Servidor HTTP do app do celular: arquivos da tela + 3 chamadas (parear, estado, conversar).

Desligado por padrão. Só responde a aparelhos pareados (token no cabeçalho Authorization). O celular conversa; o que muda
o PC continua sendo cartão aprovado na janela do PC.
"""

from __future__ import annotations

import json
import logging
import socket
import ssl
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jarvis.mobile import icones
from jarvis.mobile.pareamento import Pareamento

log = logging.getLogger(__name__)
WEB = Path(__file__).parent / "web"
MAX_CORPO = 8192
TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".webmanifest": "application/manifest+json", ".svg": "image/svg+xml"}
CSP = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"


def ip_local() -> str:
    """Endereço do PC na rede (o que o celular digita). 127.0.0.1 se não houver rede."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # não envia nada: só descobre a rota
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class ServidorCelular:
    def __init__(self, pareamento: Pareamento, responder: Callable[[str], dict], pendentes: Callable[[], int] = lambda: 0,
                 nome_usuario: str = "") -> None:
        self.pareamento, self.responder, self.pendentes, self.nome_usuario = pareamento, responder, pendentes, nome_usuario
        self._http: ThreadingHTTPServer | None = None
        self._conversa = threading.Lock()  # uma conversa por vez: o PC é fraco e o Claude tem uma sessão só
        self.url = ""

    def iniciar(self, porta: int = 8765, rede: bool = True, certificado: str = "", chave: str = "") -> str:
        servidor = self

        class Tratador(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _enviar(self, status: int, corpo: bytes, tipo: str, extra: dict | None = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", CSP)
                self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(corpo)

            def _json(self, status: int, dados: dict) -> None:
                self._enviar(status, json.dumps(dados, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

            def _aparelho(self) -> dict | None:
                cab = self.headers.get("Authorization", "")
                return servidor.pareamento.validar(cab[7:]) if cab.startswith("Bearer ") else None

            def _corpo(self) -> dict | None:
                try:
                    tamanho = int(self.headers.get("Content-Length") or 0)
                    if not 0 < tamanho <= MAX_CORPO:
                        return None
                    dados = json.loads(self.rfile.read(tamanho))
                    return dados if isinstance(dados, dict) else None
                except (ValueError, OSError):
                    return None

            def do_GET(self):
                caminho = self.path.split("?")[0]
                if caminho == "/api/estado":
                    aparelho = self._aparelho()
                    if aparelho is None:
                        return self._json(401, {"erro": "aparelho não pareado"})
                    return self._json(200, {"aparelho": aparelho["nome"], "usuario": servidor.nome_usuario, "pendentes": servidor.pendentes()})
                if caminho.startswith("/icone-") and caminho.endswith(".png"):
                    try:
                        return self._enviar(200, icones.png(int(caminho[7:-4])), "image/png")
                    except ValueError:
                        return self._json(404, {"erro": "não encontrado"})
                nome = "index.html" if caminho == "/" else caminho.lstrip("/")
                arquivo = (WEB / nome).resolve()
                if arquivo.parent != WEB.resolve() or not arquivo.is_file() or arquivo.suffix not in TIPOS:
                    return self._json(404, {"erro": "não encontrado"})
                self._enviar(200, arquivo.read_bytes(), TIPOS[arquivo.suffix])

            def do_POST(self):
                corpo = self._corpo()
                if corpo is None:
                    return self._json(400, {"erro": "pedido inválido"})
                if self.path == "/api/parear":
                    token = servidor.pareamento.trocar(str(corpo.get("codigo", "")), str(corpo.get("nome", "")))
                    return self._json(200, {"token": token}) if token else self._json(403, {"erro": "código inválido, vencido ou bloqueado"})
                if self.path == "/api/chat":
                    if self._aparelho() is None:
                        return self._json(401, {"erro": "aparelho não pareado"})
                    texto = str(corpo.get("texto", "")).strip()[:2000]
                    if not texto:
                        return self._json(400, {"erro": "mensagem vazia"})
                    with servidor._conversa:
                        resposta = servidor.responder(texto)
                    return self._json(200, {"texto": resposta.get("text") or resposta.get("error", "Sem resposta."),
                                            "cerebro": resposta.get("brain", ""), "pendentes": servidor.pendentes()})
                self._json(404, {"erro": "não encontrado"})

        host = "0.0.0.0" if rede else "127.0.0.1"
        self._http = ThreadingHTTPServer((host, porta), Tratador)
        esquema = "http"
        if certificado and chave:
            contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            contexto.load_cert_chain(certificado, chave)
            self._http.socket = contexto.wrap_socket(self._http.socket, server_side=True)
            esquema = "https"
        threading.Thread(target=self._http.serve_forever, daemon=True, name="jarvis-celular").start()
        self.url = f"{esquema}://{ip_local() if rede else '127.0.0.1'}:{self._http.server_port}"
        log.info("app do celular em %s", self.url)
        return self.url

    def parar(self) -> None:
        if self._http is not None:
            self._http.shutdown()
            self._http.server_close()
            self._http, self.url = None, ""

    @property
    def ativo(self) -> bool:
        return self._http is not None

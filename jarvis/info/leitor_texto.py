"""Texto do artigo para a leitura: baixa a página (só destino público) e extrai o texto legível.

Tudo que vem da página é DADO de terceiros: aqui só vira texto puro; nada é executado nem interpretado como pedido.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlsplit

MAX_TEXTO = 6000
MAX_BAIXADO = 1_500_000
TIMEOUT = 10
MAX_URL = 2048
_TIPOS_OK = ("text/html", "application/xhtml", "text/plain")
_IGNORAR = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg", "iframe", "template",
            "button", "select", "dialog", "canvas", "object", "embed"}
_BLOCOS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "blockquote", "ul", "ol"}
_VAZIOS = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "base", "col", "param", "track"}


class LeituraErro(Exception):
    """Falha esperada, com mensagem curta e segura para a janela (sem URL, sem detalhes internos)."""


def validar_url(url: object) -> str:
    """http/https, sem credenciais embutidas, tamanho limitado. Devolve a URL limpa ou levanta ValueError."""
    if not isinstance(url, str) or not url.strip() or len(url) > MAX_URL:
        raise ValueError("endereço inválido")
    url = url.strip()
    partes = urlsplit(url)
    host = (partes.hostname or "").lower()
    if partes.scheme not in ("http", "https") or not host or partes.username or partes.password:
        raise ValueError("só endereços http ou https, sem usuário e senha")
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost", ".localdomain")):
        raise ValueError("endereço local não é permitido")
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError("endereço de rede interna não é permitido")
    except ValueError as exc:
        if "rede interna" in str(exc):
            raise
    return url


def checar_destino(url: str) -> None:
    """Só IP público: recusa o que aponta (direto ou pelo DNS) para a própria máquina ou a rede local."""
    validar_url(url)
    host = urlsplit(url).hostname or ""
    try:
        enderecos = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            enderecos = {ipaddress.ip_address(i[4][0].split("%")[0]) for i in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
        except (OSError, ValueError):
            raise ValueError("não consegui resolver o endereço") from None
    if not enderecos or not all(e.is_global for e in enderecos):
        raise ValueError("endereço de rede interna não é permitido")


class _SoDestinoPublico(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checar_destino(newurl)  # cada salto passa pela mesma checagem
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _Extrator(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignorar = 0
        self._artigo = 0
        self.tudo: list[str] = []
        self.artigo: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _VAZIOS:
            if tag == "br":
                self._add("\n")
            return
        if tag in _IGNORAR:
            self._ignorar += 1
        elif tag in ("article", "main"):
            self._artigo += 1
        if tag in _BLOCOS:
            self._add("\n")

    def handle_endtag(self, tag):
        if tag in _VAZIOS:
            return
        if tag in _IGNORAR and self._ignorar:
            self._ignorar -= 1
        elif tag in ("article", "main") and self._artigo:
            self._artigo -= 1
        if tag in _BLOCOS:
            self._add("\n")

    def handle_data(self, data):
        self._add(data)

    def _add(self, texto: str) -> None:
        if self._ignorar:
            return
        self.tudo.append(texto)
        if self._artigo:
            self.artigo.append(texto)


def _limpar(partes: list[str]) -> str:
    texto = "".join(c for c in "".join(partes) if c.isprintable() or c == "\n")
    linhas = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in texto.split("\n"))
    return "\n".join(ln for ln in linhas if len(ln) > 1)


def extrair_texto(html: str, limite: int = MAX_TEXTO) -> str:
    """Texto legível: prefere <article>/<main>; descarta script, estilo, menu, rodapé. Nunca levanta por HTML sujo."""
    ex = _Extrator()
    try:
        ex.feed(html[:MAX_BAIXADO])
        ex.close()
    except Exception:  # noqa: BLE001 - HTML muito quebrado: usa o que já foi coletado
        pass
    principal = _limpar(ex.artigo)
    texto = principal if len(principal) >= 200 else _limpar(ex.tudo)
    if len(texto) > limite:
        corte = texto[:limite]
        fim = max(corte.rfind(". "), corte.rfind("\n"))
        texto = corte[: fim + 1] if fim > limite // 2 else corte
    return texto.strip()


def baixar_artigo(url: str, opener=None) -> str:
    """Texto do artigo (já extraído e limitado). Levanta LeituraErro com mensagem segura."""
    try:
        url = validar_url(url)
        if opener is None:  # caminho real; os testes entregam um opener falso
            checar_destino(url)
            opener = urllib.request.build_opener(_SoDestinoPublico).open
        pedido = urllib.request.Request(url, headers={"User-Agent": "SuperJarvis/1.0 (leitura)", "Accept": "text/html,text/plain"})
        with opener(pedido, timeout=TIMEOUT) as resp:
            tipo = (resp.headers.get("Content-Type") or "text/html").split(";")[0].strip().lower()
            if not tipo.startswith(_TIPOS_OK):
                raise LeituraErro("A página não é um texto que eu consiga ler.")
            html = resp.read(MAX_BAIXADO).decode("utf-8", "replace")
    except LeituraErro:
        raise
    except ValueError as exc:
        raise LeituraErro(f"Não posso abrir esse endereço: {exc}.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise LeituraErro("Não consegui baixar o artigo (sem conexão ou o site recusou).") from None
    texto = extrair_texto(html)
    if len(texto) < 40:
        raise LeituraErro("Não encontrei texto legível nessa página.")
    return texto

"""Rede do Radar: tudo que baixa da internet passa por aqui.

Defesas: só http/https; recusa endereço de rede interna (localhost, 192.168.x, 169.254.x...) mesmo
depois de redirecionamento (SSRF); limite de bytes; timeout; intervalo entre pedidos ao mesmo site;
robots.txt para ler páginas de artigo.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import time
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "SuperJarvis-Radar/1.0 (leitor de RSS pessoal; baixo volume)"
TIMEOUT = 15
LIMITE_FEED = 3_000_000
LIMITE_PAGINA = 1_500_000
INTERVALO_HOST = 0.6  # segundos entre pedidos ao mesmo site
MAX_REDIRECIONAMENTOS = 4

_ultimo: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


class RedeBloqueada(ValueError):
    """Endereço recusado por segurança (não é http/https ou aponta para a rede interna)."""


def validar_url(url: str, resolver=socket.getaddrinfo) -> str:
    partes = urllib.parse.urlparse(str(url).strip())
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise RedeBloqueada("só endereços http:// ou https:// são aceitos")
    try:
        enderecos = {info[4][0] for info in resolver(partes.hostname, partes.port or 443)}
    except OSError as exc:
        raise RedeBloqueada(f"não consegui resolver {partes.hostname}") from exc
    for texto in enderecos:
        ip = ipaddress.ip_address(texto.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise RedeBloqueada(f"{partes.hostname} aponta para a rede interna ({ip}): recusado")
    return partes.geturl()


class _Redirecionamento(urllib.request.HTTPRedirectHandler):
    """Cada destino de um redirecionamento é validado de novo, e o número de saltos é limitado."""

    max_redirections = MAX_REDIRECIONAMENTOS

    def __init__(self, resolver=socket.getaddrinfo) -> None:
        self._resolver = resolver

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validar_url(urllib.parse.urljoin(req.full_url, newurl), self._resolver)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener_padrao(resolver=socket.getaddrinfo):
    return urllib.request.build_opener(_Redirecionamento(resolver)).open


def _esperar(host: str, relogio=time.monotonic, dormir=time.sleep) -> None:
    agora = relogio()
    falta = INTERVALO_HOST - (agora - _ultimo.get(host, -1e9))
    _ultimo[host] = agora + max(0.0, falta)
    if falta > 0:
        dormir(falta)


def baixar(url: str, limite: int = LIMITE_FEED, opener=None, resolver=socket.getaddrinfo, esperar: bool = True) -> tuple[bytes, str]:
    """Baixa (bytes, content-type). `opener` injetado é para testes; sem ele valida DNS e redirecionamentos."""
    destino = validar_url(url, resolver)
    if esperar:
        _esperar(urllib.parse.urlparse(destino).netloc)
    pedido = urllib.request.Request(destino, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5"})
    with (opener or _opener_padrao(resolver))(pedido, timeout=TIMEOUT) as resp:
        tipo = resp.headers.get("Content-Type", "") if hasattr(resp, "headers") else ""
        return resp.read(limite), tipo


def decodificar(dados: bytes, tipo: str = "") -> str:
    charset = re.search(r"charset=([\w-]+)", tipo or "")
    try:
        return dados.decode(charset.group(1) if charset else "utf-8", errors="replace")
    except LookupError:
        return dados.decode("utf-8", errors="replace")


def robots_permite(url: str, opener=None, resolver=socket.getaddrinfo) -> bool:
    """O robots.txt do site deixa o Radar ler esta página? Sem robots.txt (ou com erro), vale o bom senso: sim."""
    partes = urllib.parse.urlparse(url)
    chave = f"{partes.scheme}://{partes.netloc}"
    if chave not in _robots:
        leitor = urllib.robotparser.RobotFileParser()
        try:
            dados, tipo = baixar(chave + "/robots.txt", 200_000, opener, resolver, esperar=False)
            leitor.parse(decodificar(dados, tipo).splitlines())
            _robots[chave] = leitor
        except Exception:
            _robots[chave] = None
    leitor = _robots[chave]
    return True if leitor is None else leitor.can_fetch(UA, url)

"""Links iCal das agendas. O link secreto equivale a uma senha: fica no Gerenciador de Credenciais; o config.json guarda só apelido e cor."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from jarvis import keys
from jarvis.config import Config


def _chave(apelido: str) -> str:
    return f"ical:{apelido}"


def validar_url(url: str) -> str:
    """https obrigatório (webcal:// vira https://); recusa endereço da própria máquina ou da rede local."""
    url = url.strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[9:]
    partes = urlsplit(url)
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or not host:
        raise ValueError("o link da agenda precisa começar com https:// (ou webcal://)")
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("endereço local não é permitido")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url
    if not ip.is_global:
        raise ValueError("endereço de rede interna não é permitido")
    return url


def adicionar(cfg: Config, apelido: str, url: str, cor: str = "") -> None:
    """Guarda o link no cofre e o apelido no config (quem chama salva o config)."""
    apelido = " ".join(apelido.split())[:30]
    if not apelido:
        raise ValueError("dê um apelido à agenda (ex.: Pessoal, Trabalho)")
    keys.set_key(_chave(apelido), validar_url(url))
    cfg.agendas = [a for a in cfg.agendas if a.get("apelido") != apelido] + [{"apelido": apelido, "cor": cor.strip()[:20]}]


def remover(cfg: Config, apelido: str) -> None:
    keys.delete_key(_chave(apelido))
    cfg.agendas = [a for a in cfg.agendas if a.get("apelido") != apelido]


def links(cfg: Config) -> list[dict]:
    """Agendas configuradas com o link lido do cofre. Agenda sem link no cofre é ignorada."""
    achadas = []
    for a in cfg.agendas:
        apelido = str(a.get("apelido", "")).strip()
        url = keys.get_key(_chave(apelido)) if apelido else None
        if url:
            achadas.append({"apelido": apelido, "cor": str(a.get("cor", "")), "url": url})
    return achadas

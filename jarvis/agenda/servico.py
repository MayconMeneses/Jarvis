"""Busca as agendas (com cache em disco), mescla numa timeline e responde: hoje, próximo compromisso e semana.

Um link com erro não derruba os outros: vira um aviso. O link nunca aparece em mensagem de erro nem em log.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, time as hora, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from jarvis.agenda import fontes, ics, ocorrencias, tz
from jarvis.config import Config

TTL = 15 * 60  # segundos: a agenda do Google demora a refletir mudanças, buscar mais seguido não ajuda
MAX_RESPOSTA = 5_000_000


def _pasta() -> Path:
    return fontes.pasta_cache()


def checar_destino(url: str) -> None:
    """Recusa https que aponta (direto ou pelo DNS) para a própria máquina ou a rede local: o link vem de fora e pode mentir."""
    fontes.validar_url(url)
    host = urlsplit(url).hostname or ""
    try:
        enderecos = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            enderecos = {ipaddress.ip_address(i[4][0].split("%")[0]) for i in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        except (OSError, ValueError):
            return  # sem resolver, a conexão também falha
    if not all(e.is_global for e in enderecos):
        raise ValueError("endereço de rede interna não é permitido")


class _SoDestinoPublico(urllib.request.HTTPRedirectHandler):
    """Cada redirecionamento passa pela mesma checagem (https, nada de rede interna)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checar_destino(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def baixar(url: str, opener=None) -> str:
    if opener is None:  # caminho real; os testes entregam um opener falso
        checar_destino(url)
        opener = urllib.request.build_opener(_SoDestinoPublico).open
    pedido = urllib.request.Request(url, headers={"User-Agent": "SuperJarvis/1.0 (agenda)"})
    with opener(pedido, timeout=15) as resp:
        return resp.read(MAX_RESPOSTA).decode("utf-8", "replace")


def _erro_curto(exc: Exception) -> str:
    """Motivo sem o link (que é secreto)."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"o servidor respondeu HTTP {exc.code}"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
        return "sem conexão com o servidor da agenda"
    return "resposta inválida"


def obter(apelido: str, url: str, pasta: Path, opener, agora: float) -> tuple[str, str | None]:
    """Texto iCal da agenda: do cache se tem menos de 15 minutos; se a rede falhar, a cópia antiga com aviso."""
    arq = fontes.arquivo_cache(pasta, apelido, url)
    try:
        if arq.exists() and 0 <= agora - arq.stat().st_mtime < TTL:  # relógio que voltou no tempo não congela o cache
            return arq.read_text(encoding="utf-8"), None
    except OSError:
        pass
    try:
        texto = baixar(url, opener)
        if "BEGIN:VCALENDAR" not in texto.upper():
            raise ValueError("não é um arquivo de agenda")
    except Exception as exc:  # rede, HTTP, link errado: tenta a cópia antiga
        motivo = _erro_curto(exc) if not isinstance(exc, ValueError) else str(exc)
        try:
            return arq.read_text(encoding="utf-8"), f"{apelido}: {motivo}; usando a cópia de {datetime.fromtimestamp(arq.stat().st_mtime):%d/%m %H:%M}."
        except OSError:
            raise RuntimeError(f"{apelido}: {motivo}.") from None
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        temporario = arq.with_name(f"{arq.name}.{os.getpid()}.{threading.get_ident()}.tmp")  # troca atômica: ninguém lê arquivo pela metade
        temporario.write_text(texto, encoding="utf-8")
        os.utime(temporario, (agora, agora))  # a idade do cache é medida pelo mesmo relógio
        os.replace(temporario, arq)
    except OSError:
        pass  # sem cache; segue com o que baixou
    return texto, None


def carregar(cfg: Config, ini: datetime, fim: datetime, zona=None, links: list[dict] | None = None, opener=None,
             agora: float | None = None, pasta: Path | None = None) -> dict:
    """{"ocorrencias": [Ocorrencia...], "avisos": [...]} de todas as agendas, na janela [ini, fim)."""
    zona = zona or tz.local()
    links = fontes.links(cfg) if links is None else links
    pasta, agora = pasta or _pasta(), time.time() if agora is None else agora
    listas, avisos = [], []
    if not links:
        avisos.append("Nenhuma agenda conectada. Cole o link iCal secreto da sua agenda (Google: Configurações > Endereço secreto em formato iCal).")
    for item in links:
        try:
            texto, aviso = obter(item["apelido"], item["url"], pasta, opener, agora)
            listas.append(ocorrencias.ocorrencias(ics.ler(texto), ini, fim, zona, item["apelido"], item.get("cor", "")))
            if aviso:
                avisos.append(aviso)
        except Exception as exc:  # uma agenda quebrada não derruba as outras
            avisos.append(str(exc) if isinstance(exc, RuntimeError) else f"{item['apelido']}: não consegui ler a agenda.")
    return {"ocorrencias": ocorrencias.mesclar(listas), "avisos": avisos, "sem_agendas": not links}


def _agora(zona, agora: datetime | None) -> datetime:
    return agora.astimezone(zona) if agora else datetime.now(zona)


def do_dia(cfg: Config, dia: datetime | None = None, zona=None, **kw) -> dict:
    zona = zona or tz.local()
    ref = _agora(zona, dia)
    ini = datetime.combine(ref.date(), hora(0), zona)
    return carregar(cfg, ini, ini + timedelta(days=1), zona, **kw)


def da_semana(cfg: Config, quando: datetime | None = None, zona=None, dias: int = 7, **kw) -> dict:
    zona = zona or tz.local()
    ini = datetime.combine(_agora(zona, quando).date(), hora(0), zona)
    return carregar(cfg, ini, ini + timedelta(days=dias), zona, **kw)


def proximo(cfg: Config, quando: datetime | None = None, zona=None, dias: int = 30, **kw) -> dict:
    """Próximo compromisso com horário (começa agora ou já começou e ainda não acabou). Dia inteiro só se não houver outro."""
    zona = zona or tz.local()
    ref = _agora(zona, quando)
    res = carregar(cfg, ref, ref + timedelta(days=dias), zona, **kw)
    com_hora = [o for o in res["ocorrencias"] if not o.dia_inteiro and o.fim > ref]
    res["proximo"] = com_hora[0] if com_hora else None
    return res

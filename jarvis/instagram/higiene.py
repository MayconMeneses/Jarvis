"""Higiene dos dados: datas, maturidade do post, confiança do perfil e legenda inerte."""

from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone

from jarvis.instagram import HORAS_MADURO, MAX_LEGENDA, MIN_POSTS_PERFIL

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?$")
_BR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:[ T,]+(\d{1,2})[:h](\d{2}))?$")
_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")


def epoch(texto: object) -> int | None:
    """Segundos UTC de uma data ISO (2026-10-01, 2026-10-01T10:30:00Z) ou brasileira (01/10/2026 10:30). Sem fuso = UTC."""
    t = str(texto or "").strip()
    achado = _ISO.match(t)
    if achado:
        ano, mes, dia, hora, minuto, seg, fuso = achado.groups()
    else:
        achado = _BR.match(t)
        if not achado:
            return None
        dia, mes, ano, hora, minuto = achado.groups()
        seg, fuso = None, None
    try:
        quando = datetime(int(ano), int(mes), int(dia), int(hora or 0), int(minuto or 0), int(seg or 0))
    except ValueError:
        return None
    segundos = calendar.timegm(quando.timetuple())
    if fuso and fuso != "Z":
        limpo = fuso.replace(":", "")
        desloc = (int(limpo[1:3]) * 60 + int(limpo[3:5])) * 60
        segundos -= desloc if limpo[0] == "+" else -desloc
    return segundos


def iso(segundos: int) -> str:
    return datetime.fromtimestamp(segundos, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def maturidade(post: dict, agora: int) -> str:
    """"maduro" (>= 48 h), "imaturo" (< 48 h, inclusive data no futuro) ou "sem_data" (conta como maduro, com aviso)."""
    quando = epoch(post.get("data"))
    if quando is None:
        return "sem_data"
    return "maduro" if (agora - quando) >= HORAS_MADURO * 3600 else "imaturo"


def confianca(n_maduros: int) -> str:
    return "baixa" if n_maduros < MIN_POSTS_PERFIL else "ok"


def limpar_legenda(texto: object) -> str:
    """Legenda é dado de terceiros: sem caracteres de controle, em uma linha, no máximo 200 caracteres."""
    return "".join(list(" ".join(_CONTROLE.sub(" ", str(texto or "")).split()))[:MAX_LEGENDA]).strip()

"""Uso/cota do Claude e último boletim do Radar, para o celular pareado. SOMENTE LEITURA, sem IA, sem rede.

Uso: só números (tokens do dia, janelas de 5 h e semanal, custo EQUIVALENTE em API, estimado). Nada de modelo por mensagem,
sessão, projeto nem conteúdo. Radar: só título, fonte e hora do que foi escolhido; nunca corpo nem link (texto de terceiros).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from jarvis.mobile.leitura_pc import texto_seguro

ROTULO_CUSTO = "custo equivalente estimado em API (a assinatura não cobra por token)"
AVISO_COTA = "Estimativa: o Claude não informa a cota por API."
MAX_TITULOS = 8


def _num(v, casas: int = 1):
    return round(float(v), casas) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


def _janela(j: dict) -> dict:
    pct = _num(j.get("pct"))
    return {"usado": _num(j.get("usado")) or 0.0, "teto": _num(j.get("teto")), "pct": min(pct, 999.0) if pct is not None else None,
            "ativa": j.get("ativa") is True, "alerta": j.get("alerta") is True, "msgs": int(_num(j.get("msgs"), 0) or 0),
            "fim": _num(j.get("fim"), 0), "acaba_antes_do_reset": j.get("acaba_antes_do_reset") is True}


def uso_publico(linhas_hoje: list[dict], cota: dict, agora) -> dict:
    """`linhas_hoje` = Registro.linhas(desde=meia-noite); `cota` = uso.cota.estado."""
    ia = [l for l in linhas_hoje if l.get("provedor") != "local"]
    tokens = sum(int(l["tin"]) + int(l["tout"]) + int(l["cw"]) + int(l["cr"]) for l in ia)
    return {"gerado": agora.isoformat(), "hoje": {"msgs": len(ia), "tokens": tokens,
                                                  "custo_usd": round(sum(float(l["custo"]) for l in ia), 4), "estimado": True,
                                                  "custo_rotulo": ROTULO_CUSTO},
            "cota": {"unidade": "mensagens" if cota.get("unidade") == "mensagens" else "tokens", "plano": texto_seguro(cota.get("plano"), 20),
                     "janela_5h": _janela(cota.get("janela_5h") or {}), "semana": _janela(cota.get("semana") or {}), "aviso": AVISO_COTA}}


def ler_titulos_radar(caminho: Path | None = None) -> tuple[dict | None, list[dict]]:
    """Última execução do Radar e os artigos ESCOLHIDOS nela, direto do radar.db (aberto só para leitura)."""
    from jarvis.config import data_dir

    caminho = caminho or data_dir() / "radar.db"
    if not caminho.is_file():
        return None, []
    db = sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    try:
        ex = db.execute("SELECT dia, inicio, fim, escolhidos FROM execucoes ORDER BY id DESC LIMIT 1").fetchone()
        if ex is None:
            return None, []
        arts = db.execute("SELECT fonte, titulo, quando FROM artigos WHERE escolhido=1 AND visto>=? ORDER BY visto DESC, rowid LIMIT ?",
                          (float(ex["inicio"]) - 2, MAX_TITULOS)).fetchall()
        return dict(ex), [dict(a) for a in arts]
    finally:
        db.close()


def radar_publico(execucao: dict | None, artigos: list[dict], agora) -> dict:
    if not execucao:
        return {"gerado": agora.isoformat(), "vazio": True, "dia": "", "hora": "", "total": 0, "itens": []}
    fim = execucao.get("fim")
    hora = time.strftime("%H:%M", time.localtime(float(fim))) if isinstance(fim, (int, float)) and not isinstance(fim, bool) else ""
    itens = [{"titulo": texto_seguro(a.get("titulo"), 120) or "(sem título)", "fonte": texto_seguro(a.get("fonte"), 30),
              "quando": time.strftime("%d/%m %H:%M", time.localtime(float(a["quando"]))) if isinstance(a.get("quando"), (int, float)) and a["quando"] > 0 else ""}
             for a in artigos[:MAX_TITULOS]]
    return {"gerado": agora.isoformat(), "vazio": False, "dia": texto_seguro(execucao.get("dia"), 10), "hora": hora,
            "total": max(0, min(99, int(execucao.get("escolhidos") or 0))), "itens": itens}

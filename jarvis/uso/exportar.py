"""Exportar e importar o uso (JSON completo; CSV para planilha). Só números e rótulos, nenhum texto de conversa."""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime

from jarvis.uso import configuracao, precos
from jarvis.uso.registro import Registro

MAX_LINHAS = 200_000
CAMPOS_CSV = ("data_hora", "dia", "fonte", "provedor", "modelo", "projeto", "sessao", "subagente", "tokens_in", "tokens_out",
              "cache_escrita", "cache_leitura", "custo_usd", "estimado", "preco_ok")


def _celula(valor) -> str:
    """Neutraliza fórmulas de planilha (=, +, -, @, tab, retorno) em texto vindo de fora."""
    texto = str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def exportar_json(reg: Registro) -> str:
    linhas = [{k: l[k] for k in ("ts", "fonte", "provedor", "modelo", "projeto", "sessao", "sub", "tin", "tout", "cw", "cw1h", "cr", "custo_rep")}
              for l in reg.linhas()]
    return json.dumps({"versao": 1, "linhas": linhas, "config": configuracao.carregar(reg), "precos": precos.carregar()}, ensure_ascii=False)


def exportar_csv(reg: Registro, desde: float = 0.0) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(CAMPOS_CSV)
    for l in reg.linhas(desde=desde):
        escritor.writerow([datetime.fromtimestamp(l["ts"]).isoformat(timespec="seconds"), _celula(l["dia"]), _celula(l["fonte"]),
                           _celula(l["provedor"]), _celula(l["modelo"]), _celula(l["projeto"]), _celula(l["sessao"]), int(l["sub"]), l["tin"], l["tout"], l["cw"],
                           l["cr"], f"{l['custo']:.4f}", int(l["estimado"]), int(l["preco_ok"])])
    return saida.getvalue()


def _inteiro(valor) -> int:
    try:
        return min(10**12, max(0, int(valor)))  # o SQLite guarda 64 bits: número absurdo não pode derrubar a importação
    except (TypeError, ValueError, OverflowError):
        return 0


def importar_json(reg: Registro, texto: str) -> dict:
    """Mescla um JSON exportado (as linhas repetidas não duplicam). Levanta ValueError se o arquivo não for válido."""
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError("o arquivo não é um JSON válido") from exc
    if not isinstance(dados, dict) or not isinstance(dados.get("linhas"), list):
        raise ValueError("o arquivo não parece uma exportação de uso da Jarvis")
    if len(dados["linhas"]) > MAX_LINHAS:
        raise ValueError(f"arquivo grande demais (mais de {MAX_LINHAS} linhas)")
    lote = []
    for l in dados["linhas"]:
        if not isinstance(l, dict) or not isinstance(l.get("ts"), (int, float))                 or not math.isfinite(l["ts"]) or not 0 < l["ts"] < 4e9 or not str(l.get("provedor", "")).strip():
            continue
        uso = {k: _inteiro(l.get(c)) for k, c in (("in", "tin"), ("out", "tout"), ("cw", "cw"), ("cw1h", "cw1h"), ("cr", "cr"))}
        rep = l.get("custo_rep")
        modelo, sessao = str(l.get("modelo", ""))[:80], str(l.get("sessao", ""))[:80]
        lote.append({"ts": float(l["ts"]), "fonte": "importado", "provedor": str(l["provedor"])[:30], "modelo": modelo,
                     "projeto": str(l.get("projeto", ""))[:80], "sessao": sessao, "sub": bool(l.get("sub")), "uso": uso,
                     "custo_rep": float(rep) if isinstance(rep, (int, float)) and 0 <= rep < 1e9 else None,
                     "chave": f"imp|{l['ts']}|{l['provedor']}|{modelo}|{sessao}|{uso['in']}|{uso['out']}|{uso['cw']}|{uso['cr']}"})
    reg.inserir_lote(lote)
    if isinstance(dados.get("config"), dict):
        configuracao.salvar(reg, dados["config"])
    if isinstance(dados.get("precos"), dict):
        precos.salvar(dados["precos"])
    return {"linhas": len(lote)}

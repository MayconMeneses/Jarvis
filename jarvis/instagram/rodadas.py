"""Comparar duas rodadas: medianas, outliers que entraram ou saíram, formato vencedor e ganchos que subiram."""

from __future__ import annotations


def _vencedor(resultado: dict) -> str | None:
    return resultado["formatos"][0]["formato"] if resultado["formatos"] else None


def comparar(anterior: dict, atual: dict) -> dict:
    ant = {f"{g['perfil']}|{g['formato']}": g for g in anterior["grupos"]}
    medianas = []
    for g in atual["grupos"]:
        antes = ant.get(f"{g['perfil']}|{g['formato']}")
        antes_v = antes["mediana"] if antes else None
        var = None if not antes_v else (g["mediana"] - antes_v) / antes_v
        medianas.append({"perfil": g["perfil"], "formato": g["formato"], "antes": antes_v, "agora": g["mediana"], "variacao": var,
                         "motivo": "" if antes else "formato novo nesta rodada"})
    out_a = {p["id"] for p in anterior["posts"] if p["outlier"]}
    out_b = {p["id"] for p in atual["posts"] if p["outlier"]}
    ganchos_a = {g["gancho"]: g["outliers"] for g in anterior["ganchos"]}
    subiram = [{"gancho": g["gancho"], "antes": ganchos_a.get(g["gancho"], 0), "agora": g["outliers"]}
               for g in atual["ganchos"] if g["outliers"] > ganchos_a.get(g["gancho"], 0)]
    return {"medianas": medianas, "outliers_novos": sorted(out_b - out_a), "outliers_sumidos": sorted(out_a - out_b),
            "formato_antes": _vencedor(anterior), "formato_agora": _vencedor(atual),
            "formato_mudou": _vencedor(anterior) != _vencedor(atual), "ganchos_subiram": subiram}


def texto(delta: dict, rotulo_a: str = "anterior", rotulo_b: str = "atual") -> str:
    def n(v):
        return "n/d" if v is None else f"{v:.2f}".replace(".", ",")

    linhas = [f"**Comparação: rodada {rotulo_a} x rodada {rotulo_b}**", "", "**Mediana de engajamento por perfil e formato**"]
    for m in delta["medianas"]:
        var = "n/d" if m["variacao"] is None else f"{m['variacao'] * 100:+.0f}%".replace(".", ",")
        linhas.append(f"- {m['perfil']} / {m['formato']}: {n(m['antes'])} -> {n(m['agora'])} ({var}{'; ' + m['motivo'] if m['motivo'] else ''})")
    linhas += ["", f"Outliers novos: {len(delta['outliers_novos'])}. Outliers que saíram: {len(delta['outliers_sumidos'])}."]
    for chave in delta["outliers_novos"][:5]:
        linhas.append(f"- novo: {chave}")
    if delta["formato_mudou"]:
        linhas.append(f"Formato com maior alcance mudou: {delta['formato_antes'] or 'n/d'} -> {delta['formato_agora'] or 'n/d'}.")
    else:
        linhas.append(f"Formato com maior alcance continua: {delta['formato_agora'] or 'n/d'}.")
    if delta["ganchos_subiram"]:
        linhas.append("Ganchos com mais outliers: " + ", ".join(f"{g['gancho']} ({g['antes']} -> {g['agora']})" for g in delta["ganchos_subiram"]) + ".")
    return "\n".join(linhas)

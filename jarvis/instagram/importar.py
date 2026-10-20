"""Importar posts de CSV, JSON ou texto colado (tabela). Só métricas públicas; da legenda, só o começo.

Cabeçalhos em português ou inglês; números como "1,2 mil", "3.4K", "1.234"; datas ISO ou brasileiras. Linhas ruins são
ignoradas com aviso (nunca param a importação). Cada linha é identificada pelo link do post: reimportar não duplica.
"""

from __future__ import annotations

import csv
import io
import json
import re

from jarvis.instagram import CAMPOS_NUMERICOS, fold
from jarvis.instagram.higiene import epoch, iso, limpar_legenda

MAX_TEXTO = 3_000_000
MAX_LINHAS = 3000
_SINONIMOS = {
    "perfil": "perfil arroba username usuario user profile conta handle ownerusername",
    "link": "link url permalink linkdopost posturl",
    "data": "data date datadepublicacao publicadoem publicado timestamp postedat createdat datetime",
    "formato": "formato tipo type mediatype producttype format",
    "legenda": "legenda caption texto text descricao",
    "likes": "likes curtidas like likescount",
    "comentarios": "comentarios comments comentario commentscount comment",
    "views": "views visualizacoes visualizacao plays reproducoes videoviewcount videoplaycount",
    "salvamentos": "salvamentos saves salvos saved salvamento",
    "compartilhamentos": "compartilhamentos shares compartilhados envios compartilhamento",
    "seguidores": "seguidores followers followerscount seguidor",
}
CABECALHOS = {nome: campo for campo, nomes in _SINONIMOS.items() for nome in nomes.split()}
_VAZIOS = {"", "-", "--", "n/d", "nd", "na", "n/a", "oculto", "ocultos", "hidden", "null", "none", "nan", "?"}
_MULT = {"mil": 1e3, "k": 1e3, "mi": 1e6, "m": 1e6, "milhao": 1e6, "milhoes": 1e6}
_NUM = re.compile(r"^([\d.,]+)\s*(mil|mi|milhao|milhoes|k|m)?$")
_MILHAR = re.compile(r"^\d{1,3}([.,]\d{3})+$")
_COD = re.compile(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


def numero(valor: object) -> int | None:
    """"1,2 mil" -> 1200, "3.4K" -> 3400, "1.234" -> 1234, "oculto"/"-" -> None. Texto ilegível também vira None."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return int(valor + 0.5) if valor >= 0 else None
    texto = fold(valor).strip()
    if texto in _VAZIOS:
        return None
    achado = _NUM.match(texto)
    if not achado:
        return None
    digitos, sufixo = achado.groups()
    if sufixo:
        decimal = digitos.replace(",", ".")
        if decimal.count(".") > 1:
            partes = decimal.split(".")
            decimal = "".join(partes[:-1]) + "." + partes[-1]
        try:
            return int(float(decimal) * _MULT[sufixo] + 0.5)
        except ValueError:
            return None
    if _MILHAR.match(digitos):
        return int(re.sub(r"[.,]", "", digitos))
    return int(digitos) if digitos.isdigit() else None


def normalizar_formato(valor: object) -> str:
    t = fold(valor).strip()
    if re.search(r"reel|video|clip", t):
        return "reels"
    if re.search(r"carrossel|carousel|sidecar|album", t):
        return "carrossel"
    if re.search(r"imagem|image|foto|photo|^post$", t):
        return "imagem"
    return re.sub(r"[^a-z0-9 ]", "", t)[:20].strip() or "outro"


def normalizar_perfil(valor: object) -> str:
    t = re.sub(r"^https?://(www\.)?instagram\.com/", "", str(valor or "").strip().lower()).split("/")[0].split("?")[0]
    t = re.sub(r"[^a-z0-9._]", "", t.lstrip("@"))
    return "@" + t[:30] if t else ""


def limpar_link(valor: object) -> str:
    t = str(valor or "").strip().split("?")[0].split("#")[0].rstrip("/")
    return t[:200] if t.lower().startswith("http") else ""


def chave_post(post: dict) -> str:
    """Identidade do post: o código do link (/p/XYZ e /reel/XYZ são o mesmo); sem link, perfil + data + começo da legenda."""
    link = post.get("link") or ""
    achado = _COD.search(link)
    if achado:
        return "ig:" + achado.group(1)
    if link:
        return link.lower()
    return f"{post.get('perfil')}|{post.get('data')}|{fold(post.get('legenda'))[:40]}"


def _tabela(texto: str) -> tuple[list[dict], list[str]]:
    """Linhas como dicts {coluna: texto} e avisos de linhas quebradas."""
    avisos: list[str] = []
    cru = texto.strip().lstrip("﻿")
    if cru[:1] in ("[", "{"):
        dados = json.loads(cru)
        itens = dados.get("posts", []) if isinstance(dados, dict) else dados
        return [{str(k): v for k, v in item.items()} for item in itens if isinstance(item, dict)], avisos
    cab = cru.splitlines()[0] if cru else ""
    delim = max(";\t,|", key=lambda d: cab.count(d))
    todas = [r for r in csv.reader(io.StringIO(cru), delimiter=delim) if any(c.strip() for c in r)]
    if not todas:
        return [], avisos
    cabecalho, saida = todas[0], []
    for n, linha in enumerate(todas[1:], start=2):
        while len(linha) > len(cabecalho) and not linha[-1].strip():
            linha = linha[:-1]
        if len(linha) != len(cabecalho):
            avisos.append(f"linha {n} ignorada: {len(linha)} colunas em vez de {len(cabecalho)}")
            continue
        saida.append(dict(zip(cabecalho, linha)))
    return saida, avisos


def ler(texto: str, perfil_padrao: str = "") -> dict:
    """Devolve {"posts": [...], "seguidores": {"@perfil": n}, "avisos": [...], "ignoradas": n}."""
    texto = str(texto or "")[:MAX_TEXTO]
    try:
        linhas, avisos = _tabela(texto)
    except (ValueError, csv.Error) as exc:
        raise ValueError(f"não consegui ler o texto como CSV nem JSON ({exc})") from exc
    if not linhas:
        raise ValueError("não achei nenhuma linha de posts (a primeira linha precisa ser o cabeçalho das colunas)")
    mapa = {nome: CABECALHOS.get(re.sub(r"[^a-z0-9]", "", fold(nome))) for nome in linhas[0]}
    if not any(mapa.values()):
        raise ValueError("não reconheci as colunas (use nomes como perfil, link, data, formato, legenda, likes, comentarios, views)")
    padrao, posts, vistos, seguidores, ignoradas = normalizar_perfil(perfil_padrao), [], set(), {}, 0
    for n, bruto in enumerate(linhas[:MAX_LINHAS], start=2):
        linha = {campo: bruto.get(nome) for nome, campo in mapa.items() if campo}
        perfil = normalizar_perfil(linha.get("perfil")) or padrao
        link, data_txt = limpar_link(linha.get("link")), str(linha.get("data") or "").strip()
        data = epoch(data_txt)
        if not perfil or not (link or data_txt):
            ignoradas += 1
            avisos.append(f"linha {n} ignorada: sem {'perfil' if not perfil else 'link nem data'}")
            continue
        if data_txt and data is None:
            avisos.append(f"linha {n}: data \"{data_txt[:20]}\" ilegível (post sem data)")
        post = {"perfil": perfil, "link": link, "data": iso(data) if data is not None else "",
                "formato": normalizar_formato(linha.get("formato")), "legenda": limpar_legenda(linha.get("legenda"))}
        for campo in CAMPOS_NUMERICOS:
            bruto_num = linha.get(campo)
            post[campo] = numero(bruto_num)
            if post[campo] is None and fold(bruto_num if bruto_num is not None else "").strip() not in _VAZIOS:
                avisos.append(f"linha {n}: {campo} \"{str(bruto_num)[:15]}\" ilegível (n/d)")
        chave = chave_post(post)
        if chave in vistos:
            ignoradas += 1
            avisos.append(f"linha {n} ignorada: post repetido")
            continue
        vistos.add(chave)
        posts.append(post)
        seg = numero(linha.get("seguidores"))
        if seg:
            seguidores[perfil] = seg
    if len(linhas) > MAX_LINHAS:
        avisos.append(f"só as primeiras {MAX_LINHAS} linhas foram lidas")
    return {"posts": posts, "seguidores": seguidores, "avisos": avisos, "ignoradas": ignoradas}

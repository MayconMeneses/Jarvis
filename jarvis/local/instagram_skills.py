"""Comandos de chat do analista de Instagram (sem IA): configurar, importar, relatório, comparar, pesquisar, apagar e lembrete.

As regexes rodam sobre o texto já "limpo" (minúsculo, sem acento); os handlers recebem o texto original.
"""

from __future__ import annotations

import re
from pathlib import Path

from jarvis import memory_db
from jarvis.instagram import cartoes, pesquisa, servico
from jarvis.instagram.armazenar import Armazem

PADROES = [
    ("ig_pesquisar", r"^pesquis\w+\s+(o\s+)?(perfil\s+)?(d[eo]\s+)?instagram\s+(d[eo]\s+)?@?\w[\w.]*$"),
    ("ig_importar", r"^importar posts\b[\s\S]*$"),
    ("ig_configurar", r"^configurar (a )?(analise d[eo] )?instagram\b[\s\S]*$"),
    ("ig_relatorio", r"^relatorio (de|do|sobre o) instagram$"),
    ("ig_comparar", r"^compar\w+ com a rodada anterior$|^compar\w+ (as )?rodadas$"),
    ("ig_apagar", r"^(apag\w+|exclu\w+|delet\w+)\s+(os\s+)?(dados|posts|serie)\s+(d[eo]\s+)?instagram\b.*$"),
    ("ig_lembrete", r"^(lembrete semanal d[eo] instagram\b.*\b(lig\w+|ativ\w+|deslig\w+|desativ\w+)|(lig\w+|ativ\w+|deslig\w+|desativ\w+) (o )?lembrete semanal d[eo] instagram)$"),
    ("ig_analisar", r"^(analis\w+|come\w+ (a )?analise (de |do )?)\s*(o\s+|meu\s+)?instagram$"),
]
INTENTS = {nome for nome, _ in PADROES}  # resolvidos aqui mesmo, mesmo com texto longo (tabela colada)
_EXT = {".csv", ".json", ".txt", ".tsv"}
MAX_ARQUIVO = 5_000_000


def _arm() -> Armazem:
    return Armazem()


def configurar(texto: str, cfg) -> str:
    return servico.configurar(re.sub(r"^\s*configurar\s+(a\s+)?(an[aá]lise\s+d[eo]\s+)?instagram[:\s]*", "", texto, flags=re.I))


def _arquivo(caminho: str) -> str:
    p = Path(caminho.strip().strip('"'))
    if p.suffix.lower() not in _EXT or not p.is_file():
        raise ValueError("não achei esse arquivo (use .csv, .json, .txt ou .tsv, com o caminho completo)")
    if p.stat().st_size > MAX_ARQUIVO:
        raise ValueError("arquivo grande demais (máximo 5 MB)")
    return p.read_text(encoding="utf-8-sig", errors="replace")


def importar(texto: str, cfg) -> str:
    """"importar posts C:\\x.csv" | "importar posts de @fulano" + tabela colada | "importar posts" + tabela colada."""
    primeira, _, resto = texto.strip().partition("\n")
    cabeca = re.sub(r"^\s*importar posts\s*", "", primeira, flags=re.I).strip()
    nova = bool(re.search(r"\bnova rodada\b", cabeca, re.I))
    cabeca = re.sub(r"\bnova rodada\b", "", cabeca, flags=re.I).strip()
    perfil = re.match(r"(?:de|do)\s+(@?[\w.]+)\s*$", cabeca, re.I)
    try:
        if resto.strip():
            return servico.importar(resto, perfil.group(1) if perfil else "", nova=nova)
        if cabeca and not perfil and re.search(r"[\\/]|\.\w{2,4}$", cabeca):
            return servico.importar(_arquivo(cabeca), nova=nova)
        return "Cole a tabela na linha seguinte (primeira linha com os nomes das colunas) ou diga o caminho de um arquivo .csv/.json."
    except ValueError as exc:
        return f"Não consegui importar: {exc}"


def relatorio(texto: str, cfg) -> str:
    return servico.relatorio_atual(salvar_em=memory_db.open_memory(cfg))


def comparar(texto: str, cfg) -> str:
    return servico.comparar_atual()


def analisar(texto: str, cfg) -> str:
    """Faltando configuração ou dados, diz o próximo passo; senão, entrega o relatório."""
    arm = _arm()
    if not arm.analise().get("nicho"):
        return servico.configurar("", arm) + "\n\nExemplo: configurar instagram nicho: confeitaria; meu perfil: @doces; concorrentes: @a (12 mil), @b (8,5 mil)"
    return servico.relatorio_atual(salvar_em=memory_db.open_memory(cfg), arm=arm)


def pesquisar(texto: str, cfg) -> str:
    from jarvis import keys

    alvo = re.search(r"@?([\w.]+)\s*$", texto.strip())
    r = pesquisa.seguidores_publicos(alvo.group(1) if alvo else "", brave_key=keys.get_key("brave"))
    if r["seguidores"]:
        _arm().definir_perfis({r["arroba"]: r["seguidores"]})
        return f"{r['arroba']}: cerca de {r['seguidores']:,} seguidores (fonte pública: {r['fonte']}).".replace(",", ".") + "\n" + pesquisa.AVISO
    return f"{r['arroba'] or 'perfil'}: seguidores n/d ({r['motivo']}).\n{pesquisa.AVISO}"


def apagar(texto: str, cfg) -> str:
    from jarvis.pc.actions import ActionStore

    alvo = re.search(r"(@[\w.]+)", texto)
    try:
        cartoes.propor_apagar(ActionStore(), alvo.group(1) if alvo else "tudo", "pedido no chat")
    except ValueError as exc:
        return str(exc)
    return "Deixei um cartão na janela para você aprovar a exclusão. Nada foi apagado ainda."


def lembrete(texto: str, cfg) -> str:
    from jarvis.pc.actions import ActionStore

    ligar = not re.search(r"deslig|desativ", texto, re.I)
    cartoes.propor_lembrete(ActionStore(), ligar, "pedido no chat")
    return "Deixei um cartão na janela para você aprovar. O lembrete só muda depois do Aprovar."


MODULOS = {"ig_configurar": configurar, "ig_importar": importar, "ig_relatorio": relatorio, "ig_comparar": comparar,
           "ig_analisar": analisar, "ig_pesquisar": pesquisar, "ig_apagar": apagar, "ig_lembrete": lembrete}

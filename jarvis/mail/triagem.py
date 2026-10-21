"""Visão AÇÃO / INFO / RUÍDO dos e-mails, derivada das 7 categorias existentes. Só classifica: nunca executa nada.

Ordem barata: regras do usuário -> heurística local (grátis) -> IA (ver triagem_ia.py) só para o que ficou em dúvida.
O resultado fica em cache por id do e-mail (não pergunta duas vezes). E-mail suspeito nunca vira AÇÃO.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from jarvis.config import Config, data_dir
from jarvis.mail import rules
from jarvis.mail.base import Mail

ACAO, INFO, RUIDO, SUSPEITO = "AÇÃO", "INFO", "RUÍDO", "SUSPEITO"
NIVEIS = (ACAO, INFO, RUIDO)  # o que a IA pode devolver; SUSPEITO só vem das regras de segurança

# Categoria existente -> nível.
DA_CATEGORIA = {"Importante": ACAO, "Financeiro": ACAO, "Trabalho e vagas": ACAO, "Promoções": RUIDO,
                "Notificações": INFO, "Ler depois": INFO, "Suspeito": SUSPEITO}

_ACAO = re.compile(r"\b(prazo|vence|vencimento|vencida?|boleto|fatura|pagamento|pagar|reuni[aã]o|urgente|"
                   r"confirm\w+|respond\w+|assin\w+|entrevista|convite|aprova\w+|pendente|ultimo dia|"
                   r"due|deadline|invoice|payment|action required|rsvp)\b", re.IGNORECASE)
_RUIDO = re.compile(r"\b(promo[cç][aã]o|oferta|desconto|cupom|% ?off|liquida[cç][aã]o|newsletter|descadastr\w+|"
                    r"unsubscribe|black friday|frete gr[aá]tis|imperd[ií]vel)\b", re.IGNORECASE)
_AUTOMATICO = re.compile(r"no-?reply|nao-?responda|do-?not-?reply|notifications?@|mailer-daemon", re.IGNORECASE)
MAX_CACHE, DIAS_CACHE = 2000, 60


def heuristica(mail: Mail, regras: list[dict] | None = None) -> tuple[str, bool]:
    """(nível, certo?). certo=False = ficou em dúvida e pode ir para a IA."""
    if rules.injection_reason(mail):
        return SUSPEITO, True
    categoria = rules.rule_category(mail, regras or [])
    if categoria:
        return DA_CATEGORIA[categoria], True
    texto = f"{mail.assunto} {mail.previa}"
    if mail.lista or _RUIDO.search(texto):
        return RUIDO, True
    if _ACAO.search(texto):
        return ACAO, True
    if _AUTOMATICO.search(mail.remetente):
        return INFO, True
    return INFO, False


# ── cache por id do e-mail ───────────────────────────────────────────────
def _arquivo() -> Path:
    return data_dir() / "triagem.json"


def ler_cache(arquivo: Path | None = None) -> dict:
    try:
        dados = json.loads((arquivo or _arquivo()).read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def gravar_cache(cache: dict, arquivo: Path | None = None, agora: float | None = None) -> None:
    agora = time.time() if agora is None else agora
    vivos = {k: v for k, v in cache.items() if isinstance(v, dict) and agora - v.get("t", 0) < DIAS_CACHE * 86400}
    recentes = dict(sorted(vivos.items(), key=lambda kv: kv[1].get("t", 0), reverse=True)[:MAX_CACHE])
    arquivo = arquivo or _arquivo()
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(recentes, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # sem cache só gasta mais


def classificar(cfg: Config, mails: list[Mail], perguntar_ia=None, arquivo: Path | None = None, agora: float | None = None) -> dict[str, dict]:
    """{id: {"nivel", "fonte"}}. `perguntar_ia(cfg, [Mail]) -> {id: nível}` é opcional (default: cadeia de triagem_ia)."""
    agora = time.time() if agora is None else agora
    cache = ler_cache(arquivo)
    saida: dict[str, dict] = {}
    duvida: list[Mail] = []
    for m in mails:
        nivel, certo = heuristica(m, cfg.email.regras)
        if nivel == SUSPEITO:  # segurança vale mais que o cache
            saida[m.id] = {"nivel": SUSPEITO, "fonte": "segurança"}
        elif certo:  # regra do usuário e heurística são de graça: recalcula sempre, para a edição das regras valer na hora
            saida[m.id] = {"nivel": nivel, "fonte": "regra"}
        elif m.id in cache and cache[m.id].get("nivel") in NIVEIS:  # só a resposta da IA (que custa) fica em cache
            saida[m.id] = {"nivel": cache[m.id]["nivel"], "fonte": "cache"}
        else:
            saida[m.id] = {"nivel": nivel, "fonte": "heurística"}  # provisório se a IA não puder ajudar
            duvida.append(m)
    if duvida:
        from jarvis.mail import triagem_ia

        respostas = (perguntar_ia or triagem_ia.perguntar)(cfg, duvida)
        for m in duvida:
            if respostas.get(m.id) in NIVEIS:
                saida[m.id] = {"nivel": respostas[m.id], "fonte": "ia"}
                cache[m.id] = {"nivel": respostas[m.id], "fonte": "ia", "t": agora}
    gravar_cache(cache, arquivo, agora)
    return saida


def agrupar(mails: list[Mail], niveis: dict[str, dict]) -> dict[str, list[Mail]]:
    grupos: dict[str, list[Mail]] = {ACAO: [], INFO: [], RUIDO: [], SUSPEITO: []}
    for m in mails:
        grupos[niveis.get(m.id, {}).get("nivel", INFO)].append(m)
    return grupos

"""E-mails em três baldes (AÇÃO / INFO / RUÍDO) mais os suspeitos, para comandos locais e para o briefing. Só leitura."""

from __future__ import annotations

import re

from jarvis import mail
from jarvis.config import Config
from jarvis.mail import triagem
from jarvis.mail.base import Mail, MailError


def carregar(cfg: Config, found=None, limite: int = 30, perguntar_ia=None) -> dict:
    found = mail.accounts(cfg) if found is None else found
    mails: list[Mail] = []
    avisos: list[str] = []
    if not found:
        avisos.append("Nenhuma conta de e-mail conectada.")
    for nome, conta in found.items():
        try:
            mails += conta.list_recent(limite, True)
        except MailError as exc:
            avisos.append(f"{nome}: {exc}")
    niveis = triagem.classificar(cfg, mails, perguntar_ia=perguntar_ia)
    return {"grupos": triagem.agrupar(mails, niveis), "niveis": niveis, "avisos": avisos, "sem_contas": not found}


def _assunto(m: Mail, limite: int = 70) -> str:
    return re.sub(r"\s+", " ", "".join(c for c in m.assunto if c.isprintable())).strip()[:limite] or "(sem assunto)"


def _remetente(m: Mail) -> str:
    nome = re.sub(r"<.*?>", "", m.remetente).strip().strip('"')
    return nome[:30] or m.remetente[:30]


def texto(p: dict, so_acao: bool = False) -> str:
    g = p["grupos"]
    avisos = "".join(f"\n(Aviso: {a})" for a in p["avisos"])
    if p["sem_contas"]:
        return "Nenhuma conta de e-mail conectada. Conecte com: python -m jarvis --conectar gmail (ou outlook)."
    linhas = [f"**E-mails não lidos:** {len(g[triagem.ACAO])} de ação, {len(g[triagem.INFO])} informativos, "
              f"{len(g[triagem.RUIDO])} ruído" + (f", {len(g[triagem.SUSPEITO])} suspeitos" if g[triagem.SUSPEITO] else "") + "."]
    if g[triagem.ACAO]:
        linhas.append("**Pedem ação:**")
        linhas += [f"- {_remetente(m)}: {_assunto(m)}" for m in g[triagem.ACAO][:8]]
    elif so_acao:
        linhas.append("Nenhum e-mail importante pedindo ação agora.")
    if g[triagem.SUSPEITO]:
        linhas.append(f"⚠️ {len(g[triagem.SUSPEITO])} e-mail(s) tentam dar ordens à IA e foram separados como Suspeito; revise na caixa.")
    if not so_acao:
        for rotulo, chave in (("Informativos", triagem.INFO),):
            if g[chave]:
                linhas.append(f"**{rotulo}:**")
                linhas += [f"- {_remetente(m)}: {_assunto(m)}" for m in g[chave][:5]]
    return "\n".join(linhas) + avisos


def fala(p: dict) -> str:
    """Versão falada: contagem e, no máximo, 3 assuntos de ação. Suspeitos nunca são lidos em voz alta."""
    acao = p["grupos"][triagem.ACAO]
    if p["sem_contas"] or not acao:
        return ""
    itens = "; ".join(_assunto(m, 60) for m in acao[:3])
    return f"Você tem {len(acao)} e-mail{'s' if len(acao) > 1 else ''} pedindo ação: {itens}."

"""Frases da agenda, para a janela e para a voz. Título de evento é texto de terceiros (convite de qualquer pessoa)."""

from __future__ import annotations

import re
from datetime import datetime

from jarvis.mail import rules

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def titulo_seguro(titulo: str, limite: int = 100) -> tuple[str, bool]:
    """(título sem caracteres de controle e truncado, suspeito?). Título que tenta dar ordens à IA é suspeito."""
    limpo = re.sub(r"\s+", " ", "".join(c for c in titulo if c.isprintable() or c in "\n\t")).strip()
    return limpo[:limite] or "(sem título)", rules.texto_suspeito(titulo) is not None


def linha(o, com_dia: bool = False) -> str:
    titulo, suspeito = titulo_seguro(o.titulo)
    quando = "dia inteiro" if o.dia_inteiro else f"{o.inicio:%H:%M}–{o.fim:%H:%M}" if o.fim > o.inicio else f"{o.inicio:%H:%M}"
    if com_dia:
        quando = f"{DIAS[o.inicio.weekday()]} {o.inicio:%d/%m}, {quando}"
    extra = f" · {o.local[:60]}" if o.local and not suspeito else ""
    origem = f" [{o.agenda}]" if o.agenda else ""
    return f"- {quando}: {titulo}{' ⚠️ (texto suspeito)' if suspeito else ''}{extra}{origem}"


def _avisos(res: dict) -> str:
    return "".join(f"\n(Aviso: {a})" for a in res["avisos"])


def hoje(res: dict) -> str:
    itens = res["ocorrencias"]
    if not itens:
        return ("" if res.get("sem_agendas") else "Nenhum compromisso hoje.") + _avisos(res).strip()
    return f"**Agenda de hoje ({len(itens)}):**\n" + "\n".join(linha(o) for o in itens) + _avisos(res)


def fala_hoje(res: dict) -> str:
    """Versão falada: só a contagem e os horários e títulos limpos; título suspeito nunca é lido."""
    itens = res["ocorrencias"]
    if not itens:
        return ""
    partes = []
    for o in itens[:4]:
        titulo, suspeito = titulo_seguro(o.titulo, 60)
        partes.append(("compromisso sem título confiável" if suspeito else titulo) + ("" if o.dia_inteiro else f" às {o.inicio:%H:%M}"))
    resto = f" e mais {len(itens) - 4}" if len(itens) > 4 else ""
    plural = "compromisso" if len(itens) == 1 else "compromissos"
    return f"Você tem {len(itens)} {plural} hoje: " + "; ".join(partes) + resto + "."


def proximo(res: dict) -> str:
    o = res.get("proximo")
    if o is None:
        return "Não há próximo compromisso nos próximos 30 dias." + _avisos(res)
    return "**Próximo compromisso:**\n" + linha(o, com_dia=True) + _avisos(res)


def semana(res: dict, agora: datetime) -> str:
    itens = res["ocorrencias"]
    if not itens:
        return "Nenhum compromisso nos próximos 7 dias." + _avisos(res)
    blocos, atual = [], None
    for o in itens:
        if o.inicio.date() != atual:
            atual = o.inicio.date()
            rotulo = "Hoje" if atual == agora.date() else f"{DIAS[atual.weekday()].capitalize()} {atual:%d/%m}"
            blocos.append(f"\n**{rotulo}**")
        blocos.append(linha(o))
    return "**Agenda da semana:**" + "\n".join(blocos) + _avisos(res)

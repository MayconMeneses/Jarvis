"""Relatório semanal "como estou evoluindo": domingo, uma vez por semana, texto e fala curta. Só se já houver frases medidas."""

from __future__ import annotations

from jarvis.proativo import Aviso, Contexto


def evolucao_semanal(c: Contexto) -> Aviso | None:
    if c.agora.weekday() != 6 or not (9 <= c.agora.hour < 20):
        return None
    from jarvis.local import evolucao
    from jarvis.local.aprendizado import Aprendizado

    resumo = Aprendizado().resumo(7)
    if resumo["entendidas"] + resumo["falhas"] < 5:  # pouca conversa: não vale um relatório
        return None
    texto, fala = evolucao.relatorio()
    ano, semana, _ = c.agora.isocalendar()
    return Aviso(f"evolucao:{ano}-{semana}", texto, fala)

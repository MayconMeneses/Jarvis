"""Regra do lembrete semanal do Instagram: segunda-feira, falado em voz alta (nunca entre 22h e 7h). Só se o cartão foi aprovado."""

from __future__ import annotations

from jarvis.proativo import Aviso, Contexto


def instagram_semanal(c: Contexto) -> Aviso | None:
    if not getattr(c.cfg, "instagram_lembrete", False) or c.agora.weekday() != 0 or not (9 <= c.agora.hour < 20):
        return None
    from jarvis.instagram.armazenar import ultima_rodada_em

    ultima = ultima_rodada_em()
    if ultima is None:  # sem nenhuma rodada ainda, não há o que atualizar
        return None
    dias = round((c.agora - ultima).total_seconds() / 86400)
    ano, semana, _ = c.agora.isocalendar()
    return Aviso(f"instagram:{ano}-{semana}",
                 f"📊 Instagram: faz {dias} dias da última rodada. Exporte os 12 últimos posts de cada @ e cole aqui, ou diga \"importar posts\".",
                 f"Segunda-feira: hora de atualizar a análise do Instagram. Faz {dias} dias da última rodada.", voz=True)

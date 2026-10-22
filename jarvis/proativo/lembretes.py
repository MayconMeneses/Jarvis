"""Regra dos lembretes criados por cartão aprovado (jarvis/llm/ferramentas_propostas.py): avisa quando chega a hora."""

from __future__ import annotations

from datetime import datetime, timedelta

from jarvis.proativo import Aviso, Contexto

TOLERANCIA = timedelta(days=2)  # lembrete muito antigo (PC ficou desligado) não é mais falado


def lembretes_vencidos(c: Contexto) -> Aviso | None:
    from jarvis.llm import ferramentas_propostas as propostas

    agora = c.agora.replace(tzinfo=None)
    for item in propostas.ler_lembretes():
        try:
            quando = datetime.fromisoformat(str(item["quando"]))
            texto, id_ = str(item["texto"])[:propostas.MAX_TEXTO_LEMBRETE], str(item["id"])
        except (KeyError, ValueError):
            continue
        if quando <= agora <= quando + TOLERANCIA:
            return Aviso(f"lembrete:{id_}", f"⏰ Lembrete: {texto}", f"Lembrete: {texto}", voz=True)
    return None

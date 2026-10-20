"""Cartões de aprovação do Instagram: só apagar a série de dados e ligar/desligar o lembrete semanal passam por eles.

A IA (ou o comando de chat) apenas PROPÕE; quem executa é o clique em Aprovar na janela (pc/actions.execute).
"""

from __future__ import annotations

from jarvis.instagram.armazenar import Armazem
from jarvis.instagram.importar import normalizar_perfil


def propor_apagar(store, alvo: str, motivo: str = "pedido do usuário") -> object:
    """alvo: um @ ou "tudo". Valida agora; o cartão mostra o que será apagado."""
    from jarvis.pc.actions import Action

    alvo = "tudo" if alvo.strip().lower() in ("tudo", "todos", "todas") else normalizar_perfil(alvo)
    if not alvo:
        raise ValueError("diga qual @ apagar, ou \"tudo\"")
    arm = Armazem()
    if alvo == "tudo":
        desc = f"Apagar TODOS os dados de Instagram da Jarvis: análise, perfis e {sum(r['posts'] for r in arm.rodadas())} posts em {len(arm.rodadas())} rodadas."
    else:
        n = sum(1 for r in arm.rodadas() for p in arm.posts(r["id"]) if p["perfil"] == alvo)
        desc = f"Apagar a série de {alvo} do Instagram ({n} posts guardados neste PC). Os demais perfis ficam."
    return store.save(Action("instagram_apagar", {"alvo": alvo}, desc, motivo))


def propor_lembrete(store, ligar: bool, motivo: str = "pedido do usuário") -> object:
    from jarvis.pc.actions import Action

    desc = ("Ligar o lembrete semanal do Instagram: toda segunda-feira (9h às 20h) a Jarvis FALA em voz alta para você atualizar a análise "
            "(nunca entre 22h e 7h)." if ligar else "Desligar o lembrete semanal do Instagram.")
    return store.save(Action("instagram_lembrete", {"ligar": bool(ligar)}, desc, motivo))


def executar(action) -> str:
    if action.kind == "instagram_apagar":
        alvo = action.params["alvo"]
        arm = Armazem()
        if alvo == "tudo":
            arm.apagar_tudo()
            return "Todos os dados de Instagram foram apagados deste PC."
        return f"{arm.apagar_perfil(alvo)} posts de {alvo} apagados."
    from jarvis import config

    cfg = config.load()
    cfg.instagram_lembrete = bool(action.params["ligar"])
    config.save(cfg)
    return "Lembrete semanal do Instagram ligado (segunda-feira, falado)." if cfg.instagram_lembrete else "Lembrete semanal do Instagram desligado."

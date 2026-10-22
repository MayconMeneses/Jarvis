"""Comandos do perfil do usuário: "o que você sabe sobre mim", "atualize meu perfil: tom = direto", "apague tom do meu perfil".

Ver, mudar e apagar. Mudar e apagar só criam um cartão de aprovação; nada é gravado aqui (jarvis/conversa/perfil.py).
"""

from __future__ import annotations

import re
import unicodedata

from jarvis.conversa import perfil

PADRAO = (r"^(o que (voce )?(sabe|lembra|conhece|guardou) (sobre|de) mim|me (mostra|mostre|diz|diga) (o )?(que voce sabe|meu perfil)|"
          r"(mostra|mostre|ver|veja|qual (e )?)\s*(o )?meu perfil( de usuario)?|quem sou eu para voce|"
          r"(atualiz\w+|edit\w+|mud\w+|troc\w+|defin\w+|ajust\w+)\s+(o\s+)?meu perfil\b.*|no meu perfil\b.*|"
          r"(apag\w+|remov\w+|esquec\w+|limp\w+)\s+.+\s+do meu perfil)$")
_CAMPO = r"(?P<campo>quem sou|quem eu sou|sobre mim|projetos?|preferencias?|gosto|tom de conversa|tom|jeito|metas?|objetivos?)"
_ATUALIZAR = re.compile(rf"\b{_CAMPO}\s*(?:[:=]|\be\b|\beh\b|\bsao\b|\bpara\b)\s*(?P<valor>.+)$")
_APAGAR = re.compile(rf"^(?:apag\w+|remov\w+|esquec\w+|limp\w+)\s+(?:o\s+|a\s+|os\s+|as\s+|meu\s+|minha\s+)?{_CAMPO}\s+do meu perfil$")


def _dobrar1(texto: str) -> str:
    """Tira acentos sem mudar o tamanho do texto (os índices servem para cortar o original)."""
    return "".join(unicodedata.normalize("NFD", c)[0] for c in texto).lower()


def _loja(cfg):
    from jarvis.pc import actions

    return actions.ActionStore()


def responder(texto: str, cfg, store=None) -> str:
    from jarvis import memory_db

    mem = memory_db.open_memory(cfg)
    baixo = _dobrar1(texto).strip()
    apagar = _APAGAR.match(baixo)
    if apagar:
        campo = perfil.campo_de(apagar["campo"])
        try:
            perfil.propor_apagar(store or _loja(cfg), mem, campo)
        except ValueError as exc:
            return f"Não apaguei: {exc}."
        return "Quer mesmo apagar esse campo do seu perfil? Veja o cartão e aprove ou recuse."
    if re.search(r"\b(atualiz|edit|mud|troc|defin|ajust)\w+\s+(o\s+)?meu perfil\b|^no meu perfil\b", baixo):
        achou = _ATUALIZAR.search(baixo)
        if not achou:
            return ("Diga qual campo e o novo valor, por exemplo: “atualize meu perfil: tom = direto e curto”. "
                    "Campos: " + ", ".join(perfil.CAMPOS.values()) + ".")
        valor = texto.strip()[achou.start("valor"):achou.end("valor")].strip(" .")
        try:
            perfil.propor(store or _loja(cfg), mem, perfil.campo_de(achou["campo"]), valor)
        except ValueError as exc:
            return f"Não atualizei o perfil: {exc}."
        return "Montei um cartão para atualizar o seu perfil. Aprove para eu guardar; se recusar, nada muda."
    return perfil.para_usuario(mem, cfg)

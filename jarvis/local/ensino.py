"""Ensinar a Jarvis o seu jeito de falar: "quando eu disser X, faça Y" vira uma PROPOSTA em cartão de aprovação.

Segurança: nada é gravado aqui. O cartão (ação "aprender_apelido") só grava depois do Aprovar, e o apelido guarda apenas o
ID de uma intenção segura que a Jarvis já conhece (lista fechada em frases_comandos) ou de uma explicação do autoconhecimento.
Texto livre nunca é executado: o Y precisa casar com algo conhecido, e o X é reduzido a letras, números e espaços.
"""

from __future__ import annotations

import re

from jarvis.local import autoconhecimento, casador, frases_comandos, nlp

MAX_PALAVRAS = 8
_QUANDO = re.compile(
    r"^(?:quando|se|sempre que) eu (?:disser|falar|digitar|pedir|mandar|escrever)\s+(?P<x>.+?)\s*[,;:]?\s*(?:ai\s+|entao\s+|voce\s+)*"
    r"(?:faca|faz|executa|execute|responda|responde|mostra|mostre|entenda como|significa|quer dizer|e o mesmo que)\s+(?P<y>.+)$")
_SIGNIFICA = re.compile(r"^(?!o que|que |qual|como|por que|porque|quando|onde|quem|isso|aquilo)(?P<x>[a-z0-9 ]{2,40}?)\s+(?:significa|quer dizer|e o mesmo que)\s+(?P<y>.{3,80})$")
PADRAO_ENSINAR = (r"^(?:(?:quando|se|sempre que) eu (?:disser|falar|digitar|pedir|mandar|escrever)\b.+|"
                  r"(?!o que|que |qual|como|por que|porque|quando|onde|quem|isso|aquilo)[a-z0-9 ]{2,40}?\s+(?:significa|quer dizer|e o mesmo que)\s+.{3,80})$")
APELIDAVEIS = frozenset(k for k, v in frases_comandos.INTENCOES.items() if v[2])


def _aspas(texto: str) -> str:
    return re.sub(r"[\"“”'`«»]", "", texto)


def validar_alvo(tipo: str, alvo: str) -> bool:
    return (tipo == "comando" and alvo in APELIDAVEIS) or (tipo == "conhecimento" and autoconhecimento.por_id(alvo) is not None)


def _rotulo(tipo: str, alvo: str) -> str:
    return frases_comandos.INTENCOES[alvo][0] if tipo == "comando" else autoconhecimento.por_id(alvo)["titulo"]


def resolver_alvo(motor, y: str) -> tuple[str, str] | None:
    """Y só vale se for algo que a Jarvis já sabe fazer sozinha (sem argumentos). Senão, None."""
    from jarvis.local import entendimento

    found = motor.classify(y)
    if found and found[0] in APELIDAVEIS and not found[1]:
        return "comando", found[0]
    r = entendimento.buscar(y, 2)
    m = r.melhor
    if r.nivel == casador.ALTA and m and validar_alvo(m.tipo, m.id):
        return m.tipo, m.id
    return None


def propor(motor, texto: str, store=None) -> str:
    from jarvis.local import engine
    from jarvis.local.aprendizado import frase_segura
    from jarvis.pc import actions

    baixo = _aspas(engine.clean(texto))
    achou = _QUANDO.match(baixo) or _SIGNIFICA.match(baixo)
    if not achou:
        return "Para eu aprender, diga assim: “quando eu disser bora, faça minha agenda”."
    x, y = achou["x"].strip(), achou["y"].strip()
    frase = frase_segura(x)
    if not frase or len(frase.split()) > MAX_PALAVRAS or not re.fullmatch(r"[a-z0-9 ]+", frase):
        return "Essa frase não serve de apelido: use até 8 palavras, só letras e números (sem e-mails, links ou senhas)."
    ja = motor.classify(frase)
    if ja:
        return f"Eu já entendo “{x}” como um comando ({ja[0]}). Escolha outra frase para o apelido."
    alvo = resolver_alvo(motor, y)
    if alvo is None:
        return (f"Não sei qual comando é “{y}”. Eu só aprendo apelidos para coisas que já sei fazer sozinha, "
                "como “minha agenda”, “como está o PC” ou “notícias”.")
    tipo, id_ = alvo
    rotulo = _rotulo(tipo, id_)
    acao = actions.Action(
        "aprender_apelido", {"frase": frase, "tipo": tipo, "alvo": id_},
        f"Ensinar a Jarvis: quando você disser “{frase}”, ela vai {rotulo}.",
        "Você pediu para eu aprender esse apelido. Fica só neste PC e pode ser apagado quando quiser.")
    (store or actions.ActionStore()).save(acao)
    return f"Posso aprender isto: quando você disser “{frase}”, eu vou {rotulo}. Aprove o cartão na janela para eu gravar."


def executar(params: dict) -> str:
    """Chamado só depois do Aprovar: valida de novo e grava o apelido."""
    from jarvis.local.aprendizado import Aprendizado

    frase, tipo, alvo = str(params.get("frase", "")), str(params.get("tipo", "")), str(params.get("alvo", ""))
    if not validar_alvo(tipo, alvo) or not re.fullmatch(r"[a-z0-9 ]+", frase) or len(nlp.palavras(frase)) > MAX_PALAVRAS:
        raise ValueError("apelido inválido")
    Aprendizado().gravar_apelido(frase, tipo, alvo, _rotulo(tipo, alvo))
    return f"Aprendi: quando você disser “{frase}”, eu vou {_rotulo(tipo, alvo)}."

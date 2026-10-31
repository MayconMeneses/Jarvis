"""Chamar a Jarvis por texto: o nome como vocativo no começo OU no fim de uma frase curta, e a saudação pura.

Porte de movel/js/voz-ativacao.js (extrairChamada) e movel/js/saudacao.js, com os mesmos casos compartilhados
(movel/testes/dados/ativacao_vocativo.json e saudacoes.json). Lógica pura: sem microfone, sem janela, sem disco.
O texto ouvido é dado de terceiros: aqui só se separa o nome do resto, nunca se executa nada.
"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from datetime import datetime
import time

from jarvis.voice.ativacao import _ANTES, _OUVIDO_ERRADO, _e_jarvis, _sem_acento, extrair_comando

MAX_PALAVRAS_VOCATIVO = 8
# Erros de escuta que valem no FIM da frase além do fuzzy: "avos"/"aves" ficam de fora ("visitei meus avós").
_ERRO_NO_FIM = _OUVIDO_ERRADO - {"avos", "aves"}
# Palavra logo antes do nome que mostra que se fala DO Jarvis ("o Jarvis", "filme Jarvis"), não COM ele.
_MENCAO_ANTES = {
    "o", "a", "os", "as", "um", "uma", "do", "da", "dos", "das", "no", "na", "nos", "nas", "ao", "aos", "pelo", "pela", "com", "de",
    "para", "pra", "pro", "sobre", "e", "eh", "sou", "foi", "era", "seria", "somos", "chama", "chamo", "chamado", "chamada", "nome",
    "meu", "minha", "seu", "sua", "esse", "essa", "este", "esta", "aquele", "que", "como", "tipo", "filme", "personagem", "falei",
    "falou", "disse", "amo", "adoro", "odeio", "conheco", "vi", "ouvi", "li", "assisti"}
# Como o Whisper small ouviu "Jarvis" com voz sintética pt-BR (medido). Palavras comuns: só valem com uma salvaguarda (abaixo).
_FRACO_INICIO = {"aviso", "avise", "avisa", "viz", "vis"}  # "Aviso que horas são": só se o resto for um pedido típico
_PEDIDO = re.compile(r"^(que (horas|dia)|qual|quais|quando|quanto|abre|abra|me (diz|diga|fala|fale))\b")
_FRACO_FIM = {"caviso", "caviz", "cavis", "gaviz"}  # "boa noite, Caviso": só se o resto da frase for uma saudação
_PONTUACAO = " ,.:;!?-–—…\t\n"
_CUMPRIMENTOS = {"oi", "ola", "opa"}


def _palavras(texto: str) -> list[tuple[str, int, int]]:
    return [(_sem_acento(m.group()), m.start(), m.end()) for m in re.finditer(r"\w+", texto)]


def _nome_no_fim(token: str) -> bool:
    return token in _ERRO_NO_FIM or (token not in _OUVIDO_ERRADO and _e_jarvis(token))


def _saudacao_antes_do_nome(texto: str) -> str | None:
    pal = _palavras(texto)
    i = next((k for k, (p, _, _) in enumerate(pal) if _e_jarvis(p)), -1)
    antes = [p for p, _, _ in pal[:max(i, 0)]]
    if i < 1 or not (any(p in _CUMPRIMENTOS for p in antes) or " ".join(antes) == "e ai"):
        return None
    return texto[:pal[i][1]].rstrip(_PONTUACAO).strip()


def _chamada_ouvida_errada(texto: str) -> str | None:
    """"Aviso que horas são" (= "Jarvis, que horas são" mal ouvido): só vale no começo e se o resto for um pedido típico."""
    pal = _palavras(texto)
    k = 1 if len(pal) > 1 and pal[0][0] in _ANTES | {"a"} else 0
    if k >= len(pal) or pal[k][0] not in _FRACO_INICIO:
        return None
    resto = texto[pal[k][2]:].lstrip(_PONTUACAO)
    return resto.strip() if _PEDIDO.match(_sem_acento(resto)) else None


def extrair_chamada(texto: str | None) -> str | None:
    """None = não chama a Jarvis. "" = só a chamou. Senão, o comando SEM o nome (vocativo no começo ou no fim)."""
    texto = texto or ""
    inicio = extrair_comando(texto)
    if inicio == "":
        return _saudacao_antes_do_nome(texto) or ""  # "oi Jarvis" é um cumprimento e merece resposta
    if inicio is not None:
        return inicio
    errada = _chamada_ouvida_errada(texto)
    if errada is not None:
        return errada
    pal = _palavras(texto)
    if len(pal) < 2 or len(pal) > MAX_PALAVRAS_VOCATIVO:
        return None
    k = len(pal) - 1
    cortesia = 1 if pal[k][0] == "pfv" else 2 if pal[k - 1][0] == "por" and pal[k][0] == "favor" else 0
    i = k - cortesia
    if i < 1 or pal[i - 1][0] in _MENCAO_ANTES:
        return None
    cabeca = texto[:pal[i][1]].rstrip(_PONTUACAO)
    if not _nome_no_fim(pal[i][0]) and not (pal[i][0] in _FRACO_FIM and e_saudacao(cabeca)):
        return None
    cauda = texto[pal[i][2]:].lstrip(_PONTUACAO)
    return f"{cabeca} {cauda}".rstrip(_PONTUACAO).strip()


# ── saudação pura: "oi", "boa noite", "oi, boa noite, Jarvis" (respondida sem IA, com a hora certa) ──
_NUCLEO = {"oi", "ola", "opa", "ei", "hey", "hei", "eai", "salve", "beleza", "blz"}
_ENFEITE = {"bom", "boa", "dia", "tarde", "noite", "e", "ai", "tudo", "bem", "como", "vai", "voce", "vc", "tranquilo", "fala", "ae", "jarvis"}
_NUCLEO_FRASE = re.compile(r"(bom dia|boa tarde|boa noite|(^| )e ai($| ))")
_PERGUNTA = re.compile(r"\b(tudo bem|como vai|como voce esta|tudo certo)\b")


def e_saudacao(texto: str) -> bool:
    """A frase INTEIRA é só saudação (até 6 palavras, ignorando o nome)?"""
    pal = [p for p, _, _ in _palavras(texto) if p != "jarvis" and not _e_jarvis(p)]
    if not pal or len(pal) > 6 or not all(p in _NUCLEO or p in _ENFEITE for p in pal):
        return False
    return any(p in _NUCLEO for p in pal) or bool(_NUCLEO_FRASE.search(" ".join(pal)))


def responder_saudacao(texto: str, agora: datetime | None = None, nome: str = "") -> str | None:
    """Resposta calorosa e curta, ou None se a frase não for só uma saudação."""
    if not e_saudacao(texto):
        return None
    hora = (agora or datetime.now()).hour
    quando = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    meio = " Tudo bem por aqui, e com você?" if _PERGUNTA.search(_sem_acento(texto)) else ""
    return f"{quando}{', ' + nome if nome else ''}!{meio} Estou aqui. Em que posso ajudar?"


class LimitadorAtivacao:
    """No máximo `n` ativações por texto por `janela_s`: um áudio de fundo (TV) citando o nome não vira rajada de comandos."""

    def __init__(self, n: int = 5, janela_s: float = 60.0, relogio: Callable[[], float] = time.monotonic) -> None:
        self.n, self.janela_s, self._relogio = n, janela_s, relogio
        self._marcas: deque[float] = deque()

    def permite(self) -> bool:
        agora = self._relogio()
        while self._marcas and agora - self._marcas[0] > self.janela_s:
            self._marcas.popleft()
        if len(self._marcas) >= self.n:
            return False
        self._marcas.append(agora)
        return True

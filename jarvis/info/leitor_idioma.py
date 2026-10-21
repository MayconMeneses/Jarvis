"""Detecção barata de idioma (sem rede, sem biblioteca): conta palavras funcionais de pt/en/es/fr/de/it."""

from __future__ import annotations

import re

NOMES = {"pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês", "de": "alemão", "it": "italiano"}

_PALAVRAS = {
    "pt": "o a os as um uma uns umas de do da dos das em no na nos nas por para com sem que não nao é são mais mas como foi "
          "ser tem têm você voce muito também ao aos pela pelo isso este esta está seu sua ou já ainda sobre entre depois",
    "en": "the and of to in is are was were for with that this it on as at by from be have has had not but or an they "
          "their which will would can about more been said after over also into than who",
    "es": "el la los las un una unos unas de del en y que es por con para su sus al lo como más pero fue son está han "
          "sobre entre también este esta ese ya muy sin hay sido cuando donde",
    "fr": "le la les un une des du de et en est que qui dans pour pas sur au aux avec ce cette ses son sont mais ou "
          "il elle nous vous ils plus par été être comme aussi très",
    "de": "der die das den dem des und ist ein eine einen einem von zu mit auf für nicht sich auch als bei wie nach "
          "aus über wird sind war oder aber noch nur wurde werden dass",
    "it": "il lo la i gli le un una uno di del della dei delle e che è in per con su non come più ma anche sono "
          "stato questo questa nel nella alla al dal dalla ha hanno sua suo",
}
_CONJUNTOS = {lang: set(p.split()) for lang, p in _PALAVRAS.items()}
_SINAIS = {"pt": "ãõç", "es": "ñ¿¡", "fr": "èêàûœ", "de": "äöüß", "it": "ìò"}


def detectar(texto: str) -> str:
    """Código do idioma mais provável. Pouca evidência (texto curto/sem palavras funcionais) vale como "pt": não traduz à toa."""
    baixo = (texto or "").lower()[:4000]
    palavras = re.findall(r"[a-zà-ÿñ]+", baixo)
    if len(palavras) < 4:
        return "pt"
    pontos = {lang: sum(1 for p in palavras if p in conj) for lang, conj in _CONJUNTOS.items()}
    for lang, sinais in _SINAIS.items():  # acentos típicos desempatam (ex.: es x pt x it)
        pontos[lang] += sum(baixo.count(c) for c in sinais) * 0.5
    melhor = max(pontos, key=pontos.get)
    if pontos[melhor] < 2:
        return "pt"
    return melhor

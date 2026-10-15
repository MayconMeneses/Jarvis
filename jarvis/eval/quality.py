"""Critérios de qualidade de uma resposta, sem precisar de referência (nota 0 a 10).

- clareza:    frases de tamanho legível e poucas palavras muito longas.
- fluidez:    pouca repetição, vocabulário variado, frases bem terminadas.
- relevância: a resposta trata do que foi perguntado (semântica; ou palavras-chave).
- fidelidade: cada frase da resposta tem apoio nas fontes (só quando há fontes).
- coerência:  frases vizinhas ligadas entre si, sem saltos de assunto.

São heurísticas mensuráveis e reproduzíveis, não um juiz humano. Para uma nota de
"qualidade geral" no estilo BLEURT, use o juiz por rubrica em bench.py (opcional).
"""

from __future__ import annotations

import re
from collections import Counter

from jarvis.eval import metrics

CONNECTIVES = ("porque", "portanto", "então", "além disso", "por isso", "assim", "mas", "porém", "também",
               "ou seja", "por exemplo", "primeiro", "depois", "por fim", "enquanto", "já que", "logo")


def _sentences(text: str) -> list[str]:
    clean = re.sub(r"[*_`#>]|\[\d+\]", "", text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", clean)
    return [p.strip(" -•\t") for p in parts if len(p.strip(" -•\t").split()) >= 3]


def _clamp(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 1)


def clarity(text: str) -> tuple[float, str]:
    sentences = _sentences(text)
    if not sentences:
        return 5.0, "texto curto demais para avaliar"
    lengths = [len(s.split()) for s in sentences]
    average = sum(lengths) / len(lengths)
    words = metrics.tokens(text)
    long_words = sum(1 for w in words if len(w) > 13) / max(1, len(words))
    score = 10.0
    if average > 22:
        score -= min(5, (average - 22) / 3)
    if average < 6:
        score -= 2
    score -= min(3, long_words * 40)
    return _clamp(score), f"média de {average:.0f} palavras por frase"


def fluency(text: str) -> tuple[float, str]:
    words = metrics.tokens(text)
    if len(words) < 5:
        return 7.0, "texto curto"
    trigrams = Counter(zip(words, words[1:], words[2:]))
    repeated = sum(c - 1 for c in trigrams.values() if c > 1) / max(1, len(words))
    diversity = len(set(words)) / len(words) if len(words) < 120 else len(set(words[:120])) / 120
    sentences = _sentences(text)
    unfinished = sum(1 for s in sentences if s[-1:] not in ".!?:)" and len(s.split()) > 12) / max(1, len(sentences))
    score = 10 - min(5, repeated * 60) - max(0, (0.45 - diversity) * 15) - unfinished * 2
    return _clamp(score), f"diversidade de vocabulário {diversity:.2f}"


def relevance(question: str, answer: str, encoder=None) -> tuple[float, str]:
    if encoder is not None:
        sim = encoder.similarity(question, answer[:1500])
        return _clamp((sim - 0.1) / 0.6 * 10), f"similaridade semântica pergunta↔resposta {sim:.2f}"
    from jarvis.local.websearch import keywords

    terms = set(keywords(question))
    if not terms:
        return 7.0, "pergunta sem palavras-chave"
    covered = len(terms & set(keywords(answer))) / len(terms)
    return _clamp(3 + covered * 7), f"cobre {covered:.0%} das palavras-chave da pergunta"


def fidelity(answer: str, sources: list[str], encoder=None, threshold: float | None = None) -> tuple[float | None, str]:
    """Parte das frases da resposta que tem apoio em alguma fonte."""
    if not sources:
        return None, "sem fontes para verificar"
    claims = _sentences(answer)
    if not claims:
        return None, "nada a verificar"
    source_sentences = [s for text in sources for s in _sentences(text)] or sources
    supported = 0
    for claim in claims:
        if encoder is not None:
            best = max(encoder.similarity(claim, s) for s in source_sentences[:60])
            ok = best >= (threshold or 0.7)
        else:
            best = max(metrics.rouge_l(claim, s)["precisao"] for s in source_sentences)
            ok = best >= (threshold or 0.6)
        supported += ok
    share = supported / len(claims)
    return _clamp(share * 10), f"{supported} de {len(claims)} frases com apoio nas fontes"


def coherence(text: str, encoder=None) -> tuple[float, str]:
    sentences = _sentences(text)
    if len(sentences) < 2:
        return 8.0, "uma frase só"
    pairs = list(zip(sentences, sentences[1:]))[:8]
    if encoder is not None:
        links = [encoder.similarity(a, b) for a, b in pairs]
    else:
        from jarvis.local.websearch import keywords

        links = [len(set(keywords(a)) & set(keywords(b))) / max(1, min(len(set(keywords(a))), len(set(keywords(b)))))
                 for a, b in pairs]
    average = sum(links) / len(links)
    connectives = sum(1 for c in CONNECTIVES if c in text.lower())
    score = 4 + min(5, average * (8 if encoder is not None else 10)) + min(1, connectives * 0.5)
    return _clamp(score), f"ligação média entre frases vizinhas {average:.2f}"


def evaluate(question: str, answer: str, sources: list[str] | None = None, encoder=None) -> dict:
    """Notas de 0 a 10 por critério, a média e o motivo de cada uma."""
    results = {
        "coerencia": coherence(answer, encoder),
        "clareza": clarity(answer),
        "relevancia": relevance(question, answer, encoder),
        "fidelidade": fidelity(answer, sources or [], encoder),
        "fluidez": fluency(answer),
    }
    scores = {k: v[0] for k, v in results.items()}
    valid = [v for v in scores.values() if v is not None]
    return {"notas": scores, "motivos": {k: v[1] for k, v in results.items()},
            "media": round(sum(valid) / len(valid), 1) if valid else None,
            "semantica": encoder is not None}

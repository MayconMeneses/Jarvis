"""Métricas de avaliação de texto e de classificação.

Implementações próprias e leves (rodam no PC de 8 GB, sem GPU):
- BLEU (Papineni et al., 2002): n-gramas 1–4, média geométrica, penalidade de brevidade,
  suavização epsilon (Chen & Cherry, 2014) quando um n-grama maior não casa.
- ROUGE-N e ROUGE-L (Lin, 2004): precisão, recall e F1; L usa a maior subsequência comum.
- METEOR (Banerjee & Lavie, 2005): alinhamento por palavra exata e por radical (stemmer
  Snowball de português), F-média com peso no recall e penalidade de fragmentação.
  Sem o módulo de sinônimos do WordNet, que só existe para inglês.
- BERTScore (Zhang et al., 2020): casamento guloso de embeddings de tokens com
  similaridade de cosseno, P/R/F1. Usa o MiniLM multilíngue quantizado (ver semantic.py),
  e não o RoBERTa-large do artigo; os valores não são comparáveis aos publicados.
- Precisão, recall, F1 (por classe, macro e micro), acurácia e matriz de confusão.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokens(text: str, fold_accents: bool = False) -> list[str]:
    text = text.lower()
    if fold_accents:
        text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return _TOKEN.findall(text)


def _ngrams(words: list[str], n: int) -> Counter:
    return Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def _prf(overlap: float, candidate_total: float, reference_total: float) -> dict:
    p = overlap / candidate_total if candidate_total else 0.0
    r = overlap / reference_total if reference_total else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precisao": p, "recall": r, "f1": f}


# ── BLEU ─────────────────────────────────────────────────────────────────

def bleu(candidate: str, references: list[str] | str, max_n: int = 4, smooth: bool = True) -> float:
    """BLEU de uma frase contra uma ou mais referências (0 a 1)."""
    refs = [references] if isinstance(references, str) else references
    cand = tokens(candidate)
    ref_tokens = [tokens(r) for r in refs]
    if not cand or not any(ref_tokens):
        return 0.0
    log_sum = 0.0
    for n in range(1, max_n + 1):
        cand_ngrams = _ngrams(cand, n)
        max_ref = Counter()
        for ref in ref_tokens:
            max_ref |= _ngrams(ref, n)
        clipped = sum(min(count, max_ref[g]) for g, count in cand_ngrams.items())
        total = max(len(cand) - n + 1, 0)
        if total == 0:
            return 0.0
        if clipped == 0:
            if not smooth or n == 1:
                return 0.0  # nenhuma palavra em comum: BLEU é zero
            clipped = 0.1  # suavização epsilon (Chen & Cherry, 2014, método 1)
        log_sum += math.log(clipped / total) / max_n
    closest = min((abs(len(r) - len(cand)), len(r)) for r in ref_tokens)[1]
    brevity = 1.0 if len(cand) > closest else math.exp(1 - closest / len(cand))
    return brevity * math.exp(log_sum)


# ── ROUGE ────────────────────────────────────────────────────────────────

def rouge_n(candidate: str, reference: str, n: int = 1) -> dict:
    cand, ref = _ngrams(tokens(candidate), n), _ngrams(tokens(reference), n)
    overlap = sum((cand & ref).values())
    return _prf(overlap, sum(cand.values()), sum(ref.values()))


def _lcs(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b, 1):
            current.append(previous[j - 1] + 1 if x == y else max(previous[j], current[j - 1]))
        previous = current
    return previous[-1]


def rouge_l(candidate: str, reference: str) -> dict:
    cand, ref = tokens(candidate), tokens(reference)
    return _prf(_lcs(cand, ref), len(cand), len(ref))


def rouge(candidate: str, reference: str) -> dict:
    return {"rouge1": rouge_n(candidate, reference, 1), "rouge2": rouge_n(candidate, reference, 2),
            "rougeL": rouge_l(candidate, reference)}


# ── METEOR ───────────────────────────────────────────────────────────────

def _stem(words: list[str]) -> list[str]:
    import snowballstemmer

    return snowballstemmer.stemmer("portuguese").stemWords(words)


def meteor(candidate: str, reference: str, alpha: float = 0.9, beta: float = 3.0, gamma: float = 0.5) -> float:
    """METEOR com casamento exato e por radical (0 a 1)."""
    cand, ref = tokens(candidate), tokens(reference)
    if not cand or not ref:
        return 0.0
    cand_stem, ref_stem = _stem(cand), _stem(ref)
    used: set[int] = set()
    alignment: list[tuple[int, int]] = []
    for stage in ("exato", "radical"):
        for i, word in enumerate(cand):
            if any(i == a for a, _ in alignment):
                continue
            for j in range(len(ref)):
                if j in used:
                    continue
                same = word == ref[j] if stage == "exato" else cand_stem[i] == ref_stem[j]
                if same:
                    alignment.append((i, j))
                    used.add(j)
                    break
    matches = len(alignment)
    if matches == 0:
        return 0.0
    precision, recall = matches / len(cand), matches / len(ref)
    f_mean = precision * recall / (alpha * precision + (1 - alpha) * recall)
    alignment.sort()
    chunks = 1 + sum(1 for (a1, b1), (a2, b2) in zip(alignment, alignment[1:]) if not (a2 == a1 + 1 and b2 == b1 + 1))
    penalty = gamma * (chunks / matches) ** beta
    return f_mean * (1 - penalty)


# ── BERTScore ────────────────────────────────────────────────────────────

def bertscore(candidate: str, reference: str, encoder=None) -> dict:
    """P/R/F1 por casamento guloso de embeddings de tokens (cosseno)."""
    import numpy as np

    from jarvis.eval import semantic

    encoder = encoder or semantic.default_encoder()
    cand, ref = encoder.token_embeddings(candidate), encoder.token_embeddings(reference)
    if cand.size == 0 or ref.size == 0:
        return {"precisao": 0.0, "recall": 0.0, "f1": 0.0}
    sim = cand @ ref.T  # já normalizados: produto interno = cosseno
    p, r = float(np.mean(sim.max(axis=1))), float(np.mean(sim.max(axis=0)))
    return {"precisao": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0}


# ── classificação ────────────────────────────────────────────────────────

def classification_report(expected: list[str], predicted: list[str]) -> dict:
    labels = sorted(set(expected) | set(predicted))
    per_class = {}
    for label in labels:
        tp = sum(1 for e, p in zip(expected, predicted) if e == label and p == label)
        fp = sum(1 for e, p in zip(expected, predicted) if e != label and p == label)
        fn = sum(1 for e, p in zip(expected, predicted) if e == label and p != label)
        scores = _prf(tp, tp + fp, tp + fn)
        scores["suporte"] = tp + fn
        per_class[label] = scores
    real = [l for l in labels if per_class[l]["suporte"] > 0]
    macro = {k: sum(per_class[l][k] for l in real) / len(real) if real else 0.0 for k in ("precisao", "recall", "f1")}
    correct = sum(1 for e, p in zip(expected, predicted) if e == p)
    micro = _prf(correct, len(predicted), len(expected))
    confusion = {e: dict(Counter(p for e2, p in zip(expected, predicted) if e2 == e)) for e in labels}
    return {"por_classe": per_class, "macro": macro, "micro": micro,
            "acuracia": correct / len(expected) if expected else 0.0, "confusao": confusion}

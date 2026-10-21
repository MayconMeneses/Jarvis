"""Casador de intenções SEM IA: dada uma frase solta, acha o comando ou o assunto da Jarvis mais parecido.

Roda DEPOIS das regras exatas (regex) e ANTES de desistir. Junta três sinais sobre as frases-exemplo:
BM25 (radicais, com idf), cobertura dos termos raros da pergunta e semelhança de trigramas de letras. Erros de digitação e de escuta
("javis", "celualr") são corrigidos com distância de edição contra o vocabulário conhecido antes de pontuar.
Confiança: ALTA (age), MEDIA (pergunta "Você quis dizer"), BAIXA (admite que não entendeu).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

from jarvis.local import nlp

ALTA, MEDIA, BAIXA = "alta", "media", "baixa"
LIMIAR_ALTA, LIMIAR_MEDIA, MARGEM = 0.62, 0.40, 0.08  # calibrados com a bateria retida (tests/test_entendimento_bateria.py)
K1, B = 1.4, 0.6
# Verbos e palavras de pergunta que aparecem em quase toda frase de ajuda: valem pouco para distinguir o assunto.
GENERICAS = frozenset(nlp.radical(p) for p in (
    "como onde configurar configuro usar uso usa ver vejo mostrar funciona precisa preciso fazer faz faco ficar fica ter tem "
    "quero posso pode jarvis voce vc colocar ligar ativar mudar trocar".split()))
INSTRUCIONAL = frozenset({"como", "onde", "porque", "posso", "da", "ha", "existe", "tem"})


@dataclass(frozen=True)
class Candidato:
    tipo: str      # "conhecimento" (autoconhecimento.json) ou "comando" (intenção do motor)
    id: str
    rotulo: str    # texto curto para "Você quis dizer: ..."
    score: float


@dataclass
class Resultado:
    nivel: str
    candidatos: list[Candidato] = field(default_factory=list)
    texto_corrigido: str = ""

    @property
    def melhor(self) -> Candidato | None:
        return self.candidatos[0] if self.candidatos else None


@dataclass(frozen=True)
class _Doc:
    tipo: str
    id: str
    rotulo: str
    texto: str
    peso: float
    termos: tuple[str, ...]
    tri: frozenset[str]


def _documentos(extras: tuple[tuple[str, str, str, str], ...]) -> list[tuple[str, str, str, str, float]]:
    from jarvis.local import autoconhecimento, frases_comandos

    docs = []
    for e in autoconhecimento.todos():
        for frase in e["exemplos"]:
            docs.append(("conhecimento", e["id"], e["titulo"], frase, 1.0))
        docs.append(("conhecimento", e["id"], e["titulo"], e["titulo"], 0.97))
        for palavra in e["palavras"]:
            docs.append(("conhecimento", e["id"], e["titulo"], palavra, 0.92))
    for intencao, (rotulo, exemplo, _exec, frases) in frases_comandos.INTENCOES.items():
        for frase in [exemplo, *frases]:
            docs.append(("comando", intencao, rotulo, frase, 1.0))
    for tipo, id_, rotulo, frase in extras:  # correções aprendidas: frases que o usuário já confirmou
        docs.append((tipo, id_, rotulo, frase, 1.0))
    return docs


class Indice:
    def __init__(self, extras: tuple[tuple[str, str, str, str], ...] = ()) -> None:
        brutos = _documentos(extras)
        self.vocabulario = frozenset({"jarvis"} | {p for _, _, _, t, _ in brutos for p in nlp.palavras(t) if len(p) >= 4})
        self.docs = [_Doc(t, i, r, x, p, tuple(nlp.termos(x)), frozenset(nlp.trigramas(x))) for t, i, r, x, p in brutos]
        frequencia = Counter(termo for d in self.docs for termo in set(d.termos))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in frequencia.items()}
        self.idf_desconhecido = math.log(1 + n + 0.5)
        self.medio = sum(len(d.termos) for d in self.docs) / max(1, n)

    def _idf(self, termo: str) -> float:
        base = self.idf.get(termo, self.idf_desconhecido)
        return base * 0.35 if termo in GENERICAS else base

    def _bm25(self, consulta: list[str], termos: tuple[str, ...]) -> float:
        tf, tamanho, total = Counter(termos), len(termos), 0.0
        for t in set(consulta):
            if t in tf:
                total += self._idf(t) * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * tamanho / self.medio))
        return total

    def pontuar(self, consulta: list[str], tri: frozenset[str], doc: _Doc) -> float:
        if not consulta or not doc.termos:
            return 0.0
        maximo = self._bm25(consulta, tuple(consulta)) or 1.0
        bm = min(1.0, self._bm25(consulta, doc.termos) / maximo)
        peso_total = sum(self._idf(t) for t in set(consulta))
        cobertura = sum(self._idf(t) for t in set(consulta) if t in doc.termos) / peso_total
        trig = nlp.jaccard(tri, doc.tri)
        curta = 0.8 if len(set(consulta)) == 1 else 1.0  # uma palavra só quase nunca basta para ter certeza
        return doc.peso * curta * (0.45 * bm + 0.4 * cobertura + 0.15 * trig)

    def buscar(self, texto: str, quantos: int = 3) -> Resultado:
        palavras = [nlp.corrigir(p, self.vocabulario) for p in nlp.palavras(texto)]
        corrigido = " ".join(palavras)
        consulta = nlp.termos(corrigido)
        if not consulta:
            return Resultado(BAIXA, [], corrigido)
        tri = frozenset(nlp.trigramas(corrigido))
        melhor: dict[tuple[str, str], Candidato] = {}
        for doc in self.docs:
            s = self.pontuar(consulta, tri, doc)
            chave = (doc.tipo, doc.id)
            if s > 0 and (chave not in melhor or s > melhor[chave].score):
                melhor[chave] = Candidato(doc.tipo, doc.id, doc.rotulo, round(s, 4))
        instrucional = bool(palavras) and (palavras[0] in INSTRUCIONAL or " ".join(palavras[:2]) == "por que")
        if instrucional:  # "como ver minha cota": quer o passo a passo; "minha cota": quer o dado
            melhor = {k: Candidato(c.tipo, c.id, c.rotulo, round(c.score * (1.08 if c.tipo == "conhecimento" else 0.88), 4))
                      for k, c in melhor.items()}
        melhor = _ajustar_plataforma(melhor, set(palavras))
        ordem = sorted(melhor.values(), key=lambda c: -c.score)[:quantos]
        return Resultado(_nivel(ordem), ordem, corrigido)


_CELULAR = {"celular", "iphone", "android", "telefone", "smartphone", "ipad", "ios", "safari"}
_PC = {"pc", "computador", "windows", "notebook", "laptop", "desktop"}


def _ajustar_plataforma(candidatos: dict[tuple[str, str], Candidato], palavras: set[str]) -> dict[tuple[str, str], Candidato]:
    """Se a frase fala de celular (ou de PC), as entradas só do outro lado perdem um pouco; as do mesmo lado ganham."""
    quer = "celular" if palavras & _CELULAR and not palavras & _PC else "pc" if palavras & _PC and not palavras & _CELULAR else ""
    if not quer:
        return candidatos
    from jarvis.local import autoconhecimento

    saida = {}
    for chave, c in candidatos.items():
        e = autoconhecimento.por_id(c.id) if c.tipo == "conhecimento" else None
        fator = 1.0
        if e and e["plataformas"] != ["celular", "pc"] and e["plataformas"] != ["pc", "celular"]:
            fator = 1.12 if quer in e["plataformas"] else 0.88
        saida[chave] = Candidato(c.tipo, c.id, c.rotulo, round(c.score * fator, 4))
    return saida


def _nivel(ordem: list[Candidato]) -> str:
    if not ordem:
        return BAIXA
    topo = ordem[0].score
    segundo = ordem[1].score if len(ordem) > 1 else 0.0
    if topo >= LIMIAR_ALTA and topo - segundo >= MARGEM:
        return ALTA
    return MEDIA if topo >= LIMIAR_MEDIA else BAIXA


@lru_cache(maxsize=1)
def _base() -> Indice:
    return Indice()


def indice(extras: tuple[tuple[str, str, str, str], ...] = ()) -> Indice:
    return Indice(extras) if extras else _base()


def buscar(texto: str, quantos: int = 3, extras: tuple[tuple[str, str, str, str], ...] = ()) -> Resultado:
    return indice(extras).buscar(texto, quantos)

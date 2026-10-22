"""Entendimento além das regras: o que a Jarvis faz quando nenhuma regra (regex) casa a frase. Sem IA.

Ordem: apelido ensinado pelo usuário, depois o casador (alta confiança age; média pergunta "Você quis dizer"; baixa admite
que não entendeu e oferece as opções mais próximas e a pesquisa). Nunca devolve o bloco genérico de funções.
Aprende localmente (jarvis/local/aprendizado.py): o que não entendeu, o que o usuário corrigiu e o que ensinou.
"""

from __future__ import annotations

import re
import time
import zlib

from jarvis.local import autoconhecimento, casador, frases_comandos, nlp
from jarvis.local.casador import ALTA, MEDIA, Candidato

VALIDADE_PENDENTE = 180  # segundos que "1, 2 ou 3" continua valendo
_ESCOLHA = re.compile(r"^(?:a\s+|o\s+)?(?:(?P<n>[123])|(?P<p>primeir[ao]|um|segund[ao]|dois|terceir[ao]|tres)|(?P<s>sim|isso|isso mesmo|pode ser|esse|essa|aham|claro))$")
_NAO = re.compile(r"^(?:nao|nenhum[ao]?|nenhuma delas|nada disso|deixa|esquece|cancela)$")
_POSICAO = {"primeiro": 0, "primeira": 0, "um": 0, "segundo": 1, "segunda": 1, "dois": 1, "terceiro": 2, "terceira": 2, "tres": 2}
# Frases que a Jarvis não deve tomar por pergunta de mundo (ir para a internet): falam dela ou do uso dela.
_QUESTAO_MUNDO = re.compile(r"^(o que|quem|qual|quais|como|quando|onde|por que|porque|quanto|explique|defina)\b")


def _extras() -> tuple:
    try:
        from jarvis.local.aprendizado import Aprendizado

        return Aprendizado().extras_do_casador()
    except Exception:  # o aprendizado nunca atrapalha a resposta
        return ()


def _aprender(acao, *args) -> None:
    try:
        from jarvis.local.aprendizado import Aprendizado

        getattr(Aprendizado(), acao)(*args)
    except Exception:
        pass


def buscar(texto: str, quantos: int = 3):
    return casador.buscar(texto, quantos, _extras())


# ── executar o que o casador achou ───────────────────────────────────────

def _rotulo(c: Candidato) -> str:
    return c.rotulo


def executar(motor, c: Candidato, texto: str) -> str:
    if c.tipo == "conhecimento":
        e = autoconhecimento.por_id(c.id)
        return autoconhecimento.formatar(e) if e else "Não encontrei essa explicação."
    if frases_comandos.INTENCOES[c.id][2]:
        return motor.executar(c.id, texto, {})
    exemplo = frases_comandos.INTENCOES[c.id][1]
    return f"Para {c.rotulo} eu preciso de um nome ou assunto. Diga, por exemplo: “{exemplo}”."


def _executavel(c: Candidato) -> bool:
    return c.tipo == "conhecimento" or (c.id in frases_comandos.INTENCOES and frases_comandos.INTENCOES[c.id][2])


# ── apelidos e escolha ───────────────────────────────────────────────────

def apelido(motor, texto: str) -> str | None:
    try:
        from jarvis.local.aprendizado import Aprendizado

        achou = Aprendizado().apelido(texto)
    except Exception:
        return None
    if not achou:
        return None
    tipo, alvo, rotulo = achou
    if tipo == "comando" and alvo not in frases_comandos.INTENCOES:
        return None
    if tipo == "conhecimento" and not autoconhecimento.por_id(alvo):
        return None
    return executar(motor, Candidato(tipo, alvo, rotulo, 1.0), texto)


def escolher_pendente(motor, texto: str) -> str | None:
    """Resposta a um "Você quis dizer": 1, 2, 3, "a segunda", "sim" ou "não". None = não é uma escolha."""
    pendente = getattr(motor, "_pendente", None)
    if not pendente:
        return None
    if time.monotonic() - pendente["quando"] > VALIDADE_PENDENTE:
        motor._pendente = None
        return None
    baixo = " ".join(nlp.palavras(texto))
    if _NAO.match(baixo):
        motor._pendente = None
        return f"Tudo bem. Se quiser que eu procure na internet, diga “pesquisa {pendente['frase']}”."
    m = _ESCOLHA.match(baixo)
    if not m:
        return None
    pos = int(m["n"]) - 1 if m["n"] else _POSICAO.get(m["p"], 0) if m["p"] else 0
    opcoes = pendente["opcoes"]
    if pos >= len(opcoes):
        return None
    motor._pendente = None
    escolhida = opcoes[pos]
    _aprender("registrar_correcao", pendente["frase"], escolhida.tipo, escolhida.id, escolhida.rotulo)
    _aprender("contar", True)
    return executar(motor, escolhida, pendente["frase"])


# ── quando a regra não casou ─────────────────────────────────────────────

def conhecimento_alto(texto: str) -> Candidato | None:
    """Alta confiança em uma explicação sobre a própria Jarvis (vai antes de pesquisa/algoritmo genéricos)."""
    r = buscar(texto, 2)
    return r.melhor if r.nivel == ALTA and r.melhor.tipo == "conhecimento" else None


def duvida_sobre_mim(motor, texto: str) -> str | None:
    """Pergunta que parece ser sobre a própria Jarvis, mas ambígua (ex.: "como faço backup": PC ou celular?): pergunta em vez de pesquisar."""
    r = buscar(texto)
    opcoes = [c for c in r.candidatos if c.tipo == "conhecimento" and c.score >= 0.30][:3]
    if r.nivel != MEDIA or not opcoes or opcoes[0].score < 0.5:
        return None
    motor._pendente = {"quando": time.monotonic(), "frase": " ".join(nlp.palavras(texto)), "opcoes": opcoes}
    return f"Você quis dizer:\n{_opcoes_texto(opcoes)}\nResponda 1, 2 ou 3 (ou “não”)."


def _dica(texto: str, melhor: Candidato | None) -> str:
    """Uma dica curta e contextual; varia com a frase (nunca o mesmo bloco)."""
    if melhor and melhor.tipo == "conhecimento":
        e = autoconhecimento.por_id(melhor.id)
        return f"Dica: pergunte “{e['exemplos'][0]}”."
    chaves = [k for k, v in frases_comandos.INTENCOES.items() if v[2]]
    escolhidas = [frases_comandos.INTENCOES[chaves[(zlib.crc32(texto.encode()) + i * 7) % len(chaves)]][1] for i in range(3)]
    return "Dica: eu entendo coisas como " + ", ".join(f"“{e}”" for e in dict.fromkeys(escolhidas)) + "."


def _opcoes_texto(opcoes: list[Candidato]) -> str:
    return "\n".join(f"{n}. {_rotulo(c)}" for n, c in enumerate(opcoes, 1))


def fallback(motor, texto: str, cfg=None) -> str:
    from jarvis.local import engine

    low = engine.clean(texto)
    apelidado = apelido(motor, texto)
    if apelidado is not None:
        _aprender("contar", True)
        return apelidado
    r = buscar(texto)
    topo = r.melhor
    if r.nivel == ALTA and _executavel(topo):
        _aprender("contar", True)
        return executar(motor, topo, texto)
    pergunta_de_mundo = len(low.split()) >= 3 and (texto.strip().endswith("?") or _QUESTAO_MUNDO.match(low))
    if pergunta_de_mundo and (topo is None or topo.tipo == "comando" or topo.score < 0.30):
        _aprender("contar", True)
        return motor._pesquisa(texto, tema=low)  # nada na Jarvis se parece com isso: é uma pergunta sobre o mundo
    _aprender("registrar_falha", texto)
    _aprender("contar", False)
    opcoes = [c for c in r.candidatos if c.score >= 0.18][:3]
    if r.nivel in (ALTA, MEDIA) and opcoes:
        motor._pendente = {"quando": time.monotonic(), "frase": low, "opcoes": opcoes}
        return (f"Você quis dizer:\n{_opcoes_texto(opcoes)}\n"
                "Responda 1, 2 ou 3 (ou “não”). Se preferir a internet, diga “pesquisa " + low[:60] + "”.")
    motor._generico = True  # LocalEngine.ask troca este bloco pela orientação de como ligar um cérebro generativo
    partes = [f"Não entendi “{texto.strip()[:80]}”."]
    if opcoes:
        motor._pendente = {"quando": time.monotonic(), "frase": low, "opcoes": opcoes}
        partes.append("As coisas mais próximas que eu sei fazer:\n" + _opcoes_texto(opcoes) + "\nResponda 1, 2 ou 3 se for uma delas.")
    partes.append(f"Quer que eu pesquise na internet? Diga “pesquisa {low[:60]}”." if low else "")
    if cfg is not None and not getattr(cfg, "somente_independente", False):
        partes.append("Com uma IA ligada (Claude, Gemini ou NVIDIA) ela pode responder por mim.")
    partes.append(_dica(texto, topo))
    partes.append("Você pode me ensinar: “quando eu disser X, faça Y”.")
    return "\n".join(p for p in partes if p)


# ── ligação com o roteador de cérebros ───────────────────────────────────

def rota_local(texto: str) -> bool:
    """True se o motor próprio tem a resposta certa (alta confiança em autoconhecimento): responde na hora, sem gastar IA."""
    try:
        return conhecimento_alto(texto) is not None
    except Exception:
        return False


def contexto_para_ia(texto: str) -> str:
    """RAG: trechos do autoconhecimento mais próximos da pergunta, para a IA responder sobre a Jarvis com fidelidade ao código."""
    try:
        r = buscar(texto, 3)
        ids = [c.id for c in r.candidatos if c.tipo == "conhecimento" and c.score >= 0.30]
        trecho = autoconhecimento.contexto_para_ia(ids) if ids else ""
    except Exception:
        return ""
    return ("\n\nSobre a própria Jarvis (fatos conferidos com o código; use apenas isto e não invente recursos):\n" + trecho) if trecho else ""

"""Monta o prompt do modelo pequeno: persona + conhecimento curado da Jarvis (RAG) + memória do usuário.

Um modelo de 1,5 a 3 bilhões de parâmetros erra muito de memória; entregar a ele o trecho certo da base curada
(tópicos, padrões, algoritmos, tecnologias) e da memória do usuário melhora bastante as respostas.
"""

from __future__ import annotations

PERSONA = (
    "Você é a Jarvis, assistente pessoal e parceira de programação de {nome}. Responda em português do Brasil, "
    "de forma curta e direta. Pense antes de responder: entenda o pedido, escolha o caminho mais simples e só então escreva. "
    "Se não souber, diga que não sabe em vez de inventar. Em código, escreva funções pequenas, com nomes claros e sem "
    "dependências desnecessárias. Nunca peça nem repita senhas ou chaves."
)
LIMITE_TRECHO = 900
LIMITE_TOTAL = 3200
MAX_HISTORICO = 6
MAX_CHARS_MENSAGEM = 1500


def _cortar(texto: str, limite: int = LIMITE_TRECHO) -> str:
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


def conhecimento(pergunta: str) -> list[str]:
    """Trechos da base curada que combinam com a pergunta (no máximo 3)."""
    from jarvis.dev import conhecimento as tecnologias
    from jarvis.dev import engenharia, logica, saber

    trechos: list[str] = []
    try:
        padrao, algoritmo = engenharia.padrao(pergunta), logica.algorithm(pergunta)
        linguagem = logica.language_in(pergunta)
        if padrao:
            trechos.append(_cortar(engenharia.mostrar_padrao(padrao, linguagem), 1400))
        if algoritmo:
            trechos.append(_cortar(logica.show(algoritmo, linguagem), 1400))
        from jarvis.dev import topicos

        trechos += [_cortar(topicos.descrever(item)) for _, item in saber.citados(pergunta)[:2]]
        trechos += [_cortar(tecnologias.describe(item)) for item in tecnologias.mentioned(pergunta)[:2]]
    except Exception:  # a base curada nunca derruba a conversa
        pass
    return trechos[:3]


def memoria(pergunta: str, cfg) -> list[str]:
    if cfg is None:
        return []
    try:
        from jarvis import memory_db

        return [f"- {a['nota']}: {a['trecho']}" for a in memory_db.open_memory(cfg).search(pergunta, 3)]
    except Exception:
        return []


def sistema(base: str, pergunta: str, cfg=None) -> str:
    """Persona + (instruções recebidas) + conhecimento e memória relevantes, sem passar do limite de contexto."""
    nome = getattr(cfg, "user_name", "") or "Maycon"
    partes = [PERSONA.format(nome=nome)]
    extra = conhecimento(pergunta)
    if extra:
        partes.append("Conhecimento confiável para usar na resposta:\n" + "\n\n".join(extra))
    lembrancas = memoria(pergunta, cfg)
    if lembrancas:
        partes.append("O que você lembra do usuário:\n" + "\n".join(lembrancas))
    return _cortar("\n\n".join(partes), LIMITE_TOTAL)


def historico(mensagens: list[dict]) -> list[dict]:
    """Só as últimas mensagens, cada uma limitada: o contexto do modelo pequeno é curto."""
    return [{"role": m["role"], "content": _cortar(m["content"], MAX_CHARS_MENSAGEM)} for m in mensagens[-MAX_HISTORICO:]]

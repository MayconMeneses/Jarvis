"""RAG da conversa: escolhe por relevância o que da base da Jarvis ajuda a responder esta pergunta.

Três fontes, todas locais: notas do usuário (memória), conhecimento curado de programação (jarvis/dev) e o autoconhecimento
da Jarvis. Só entra o que combina com palavras-chave da pergunta (ou do assunto em andamento, nos acompanhamentos).
"""

from __future__ import annotations

import logging

from jarvis.conversa import privacidade
from jarvis.conversa.reescrita import dobrar

log = logging.getLogger(__name__)
_PARADAS = set("""para como qual quais quando onde porque pelo pela pelos pelas sobre entre ainda mais menos muito muita
isso essa esse aquilo aquele dele dela eles elas voce voces tenho tinha estou estar esta estao fazer faco fazem pode posso
preciso quero queria gostaria deve devo vale quanto quantos quantas algum alguma algo nada tudo todo toda todos todas
depois antes agora hoje ontem entao tambem sempre nunca melhor pior diferenca exemplo""".split())
IGNORAR = ("Diário/", "Relatórios/")


def palavras_chave(texto: str, maximo: int = 8) -> list[str]:
    achadas: list[str] = []
    for palavra in dobrar(texto).split():
        palavra = "".join(c for c in palavra if c.isalnum())
        if len(palavra) > 3 and palavra not in _PARADAS and palavra not in achadas:
            achadas.append(palavra)
    return achadas[:maximo]


def notas(mem, consulta: str, nuvem: bool, quantas: int = 3) -> list[str]:
    termos = palavras_chave(consulta)
    if mem is None or not termos:
        return []
    try:
        achados = mem.search(" ".join(termos), 12)
    except Exception:
        log.info("busca nas notas indisponível", exc_info=True)
        return []
    linhas: list[str] = []
    for a in achados:
        ref = a["nota"]
        if ref.startswith(IGNORAR) or ref == "Perfil do Usuário" or (nuvem and privacidade.area_sensivel(ref)):
            continue
        trecho = privacidade.redigir(a["trecho"]) if nuvem else a["trecho"]
        linhas.append(f"- {ref}: {trecho}")
        if len(linhas) >= quantas:
            break
    return linhas


def conhecimento(consulta: str) -> list[str]:
    """Trechos curados (padrões, algoritmos, tópicos, tecnologias) que combinam com a pergunta."""
    from jarvis.llm import contexto

    return contexto.conhecimento(consulta)


def sobre_a_jarvis(consulta: str) -> str:
    """Fatos conferidos com o código quando a pergunta fala da própria Jarvis (vazio se nada combina)."""
    try:
        from jarvis.local import entendimento

        return entendimento.contexto_para_ia(consulta).strip()
    except Exception:
        return ""

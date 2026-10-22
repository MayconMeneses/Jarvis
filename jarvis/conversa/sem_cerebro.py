"""O que a Jarvis diz quando nenhum cérebro generativo está disponível: o caminho para ligar um, nunca silêncio nem o bloco genérico."""

from __future__ import annotations

GEMINI_URL = "https://aistudio.google.com/apikey"
ATALHOS = [{"rotulo": "Abrir ⚙ Cérebros", "acao": "cerebros"}, {"rotulo": "Chave Gemini grátis", "url": GEMINI_URL}]
PASSOS = (
    "Para conversar de verdade eu preciso de um cérebro generativo ligado. Escolha um:\n"
    f"1. Gemini, grátis e o mais rápido de ligar: crie uma chave em {GEMINI_URL} e cole em ⚙ Cérebros (menu da janela).\n"
    "2. Claude, se você tem a assinatura: instale o Claude Code e entre com a sua conta (rode `claude` uma vez no terminal).\n"
    "3. Cérebro local, sem internet e sem custo: diga “instalar cérebro local” (roda no seu PC, mais simples que os outros).\n"
    "Enquanto isso eu continuo fazendo comandos (abrir programas, hora, clima, notícias, pesquisa) e respondendo sobre mim."
)


def texto(pergunta: str = "", somente_independente: bool = False) -> str:
    """Resposta amigável para uma conversa aberta quando só o motor de regras está de pé."""
    abertura = "Isso é uma conversa aberta, e sem um cérebro generativo eu só te daria uma resposta vaga."
    if somente_independente:
        return (abertura + " O modo “somente independente” está ligado, então não uso Claude, Gemini nem NVIDIA. "
                "Desligue-o em ⚙ Cérebros para conversar, ou instale o cérebro local (“instalar cérebro local”).")
    return abertura + "\n\n" + PASSOS


def erro(falhas: list[str]) -> str:
    """Mensagem do NoBrainAvailable: o motivo técnico de cada cérebro e o caminho para resolver."""
    motivo = "; ".join(falhas) if falhas else "nenhum cérebro está ligado"
    return f"nenhum cérebro respondeu ({motivo}).\n\n{PASSOS}"

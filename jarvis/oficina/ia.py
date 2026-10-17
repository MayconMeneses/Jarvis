"""Criar com IA na Oficina: planeja os arquivos, escreve um por vez, roda os testes no sandbox e corrige; mostra o resultado.

A IA pode ser o cérebro local (sem API) ou qualquer cérebro do roteador (Claude, Gemini, NVIDIA): `conversa_do_roteador`.
Clicar em "Criar com IA" é o consentimento para gerar e testar; rodar o programa em si continua sendo outro clique.
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.llm import pensar
from jarvis.oficina import sandbox

Conversa = Callable[[list[dict]], str]


def conversa_do_roteador(router, system: str = "") -> Conversa:
    """Adapta o roteador de cérebros (Claude, Gemini, NVIDIA, modelo local) ao formato das habilidades de criação."""
    def conversa(mensagens: list[dict]) -> str:
        sistema = "\n\n".join(m["content"] for m in mensagens if m["role"] == "system") or system
        dialogo = [{"role": m["role"], "content": m["content"]} for m in mensagens if m["role"] != "system"]
        return router.ask(dialogo, sistema).text
    return conversa


def criar(descricao: str, conversa: Conversa, cfg=None, status: Callable[[str], None] | None = None, nome: str = "Projeto") -> dict:
    """{arquivos, avisos, linguagem, principal, testes} com os testes JÁ rodados no sandbox (texto do resultado em `testes`)."""
    resultado = pensar.criar(nome, descricao, conversa, cfg, status)
    arquivos = {c: t for c, t in resultado.arquivos.items() if c != "README.md" or len(resultado.arquivos) == 1}
    linguagem = "javascript" if any(c.endswith(".js") for c in arquivos) and not any(c.endswith(".py") for c in arquivos) else "python"
    principal = next((c for c in arquivos if c.endswith(".py" if linguagem == "python" else ".js") and not c.split("/")[-1].startswith("test")), "")
    testes = ""
    if any(c.split("/")[-1].startswith(("test_", "test")) for c in arquivos):
        testes = sandbox.testar(linguagem, arquivos).texto()
    return {"arquivos": resultado.arquivos, "avisos": resultado.avisos, "linguagem": linguagem, "principal": principal, "testes": testes}

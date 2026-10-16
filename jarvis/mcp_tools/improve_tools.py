"""Autoaperfeiçoamento: caderno de melhorias e "Jarvis, melhore-se"."""

from __future__ import annotations

from jarvis import config, selfimprove
from jarvis.mcp_tools.core import proposal, server, store, vault
from jarvis.pc import actions


def _notebook_vault():
    """Cofre do Obsidian se houver; senão o caderno fica na pasta de dados da Jarvis."""
    try:
        return vault()
    except ValueError:
        return None


@server.tool()
def anotar_melhoria(ideia: str) -> str:
    """Anota no caderno de melhorias (Obsidian: Jarvis/Melhorias.md) algo que a Jarvis deveria fazer
    melhor. Use quando o usuário pedir ("anota uma melhoria: ...") ou quando você mesmo notar uma
    limitação que ele sentiu. Não duplica ideias parecidas."""
    added = selfimprove.add_idea(ideia, "anotada na conversa", _notebook_vault())
    return "Melhoria anotada no caderno." if added else "Essa ideia já está no caderno (ou é curta demais)."


@server.tool()
def listar_melhorias() -> list[dict] | str:
    """Ideias de melhoria ainda abertas no caderno (da mais antiga à mais nova)."""
    ideas = selfimprove.list_ideas(_notebook_vault())
    return ideas or "O caderno de melhorias está vazio."


@server.tool()
def propor_melhorar_se(ideia: str = "") -> str:
    """"Jarvis, melhore-se": propõe que o Claude Code altere o código da própria Jarvis para
    implementar UMA melhoria (a que o usuário disser ou a mais antiga do caderno). Só roda depois
    que o usuário aprovar o cartão; depois de "Manter" rodam os testes e o benchmark. Funciona
    só na cópia de desenvolvimento (a versão instalada não altera o próprio código)."""
    ideia = ideia.strip()
    if not ideia:
        open_ideas = selfimprove.list_ideas(_notebook_vault())
        if not open_ideas:
            return "O caderno de melhorias está vazio: diga o que quer melhorar."
        ideia = open_ideas[0]["ideia"]
    try:
        cfg = config.load()
        name = selfimprove.ensure_registered(cfg)
        config.save(cfg)
        return proposal(actions.propose_dev_task(
            store, cfg, name, selfimprove.task_for(ideia), f"melhoria da própria Jarvis: {ideia[:120]}"))
    except ValueError as exc:
        return f"Não é possível propor: {exc}"

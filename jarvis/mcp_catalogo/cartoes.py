"""Cartões de aprovação para instalar, desativar e remover ferramentas externas do catálogo.

PROPOR só monta o cartão (fonte, versão, comando exato, permissões, riscos). Nada é baixado, gravado ou executado antes do
Aprovar. EXECUTAR (só após o Aprovar, via jarvis/pc/actions.py) revalida TUDO: entrada no catálogo, versão fixada, pré-requisito,
hash no registro e teste de saúde; só então grava o registro e o `mcp.json`. Sem sudo, sem texto arbitrário, só no perfil do usuário.
"""

from __future__ import annotations

import logging

from jarvis.config import data_dir
from jarvis.mcp_catalogo import catalogo, instalados, integridade, saude

log = logging.getLogger(__name__)
KINDS = ("instalar_mcp", "remover_mcp")


def listar_texto() -> str:
    linhas = ["**Ferramentas externas que a Jarvis sabe instalar** (curadas; só o Claude CLI as usa; você aprova cada uma num cartão):"]
    for item in catalogo.itens():
        reg = instalados.registro_de(item["id"])
        marca = " — instalada" if reg and reg.get("ativo") else ""
        linhas.append(f"- **{item['nome']}** [{item['id']}] v{item['versao']}, risco {item['risco']}{marca}: {item['descricao']}")
    linhas.append('\nDiga "instalar a ferramenta <nome>" para ver o cartão. Para remover: "remover a ferramenta <nome>". '
                  'Recusadas de propósito: "ferramentas recusadas".')
    return "\n".join(linhas)


def recusados_texto() -> str:
    return "**Ferramentas populares que a Jarvis NÃO instala, e por quê:**\n" + "\n".join(
        f"- {r['pacote']}: {r['motivo']}" for r in catalogo.recusados())


def _descricao(item: dict, pre: str) -> str:
    programa, argumentos, _ = catalogo.comando(item, str(data_dir()))
    integ = "sha512 do npm" if item["gerenciador"] == "npx" else "sha256 do PyPI"
    return (
        f"Instalar a ferramenta externa “{item['nome']}” para o Claude CLI.\n"
        f"Fonte: {item['fonte']} (registro: {item['registro']}). Mantenedor: {item['mantenedor']}. Licença: {item['licenca']}.\n"
        f"Versão FIXADA: {item['versao']} (publicada em {item['publicado_em']}; {item['dependencias_diretas']} dependências diretas). "
        f"Conferência de integridade: {integ} comparado com o registro antes de ligar.\n"
        f"Comando exato: {programa} {' '.join(argumentos)}\n"
        f"O que faz: {item['descricao']}\n"
        f"Permissões: {'; '.join(item['permissoes'])}.\n"
        f"Risco {item['risco']}: {' '.join(item['riscos'])}\n"
        f"Pré-requisito: {pre}\n"
        "Ao aprovar: confiro o pacote no registro, abro o servidor uma vez só para listar as ferramentas e então o ligo. "
        "Dá para desativar ou remover quando quiser.")


def propor_instalar(termo: str, store, verificar=None, achar_prereq=None) -> str:
    item = catalogo.achar(termo)
    if item is None:
        return "Não conheço essa ferramenta no catálogo curado.\n" + listar_texto()
    reg = instalados.registro_de(item["id"])
    if reg and reg.get("ativo") and reg.get("versao") == item["versao"]:
        return f"“{item['nome']}” já está instalada e ativa (v{item['versao']})."
    caminho, pre = (achar_prereq or saude.prerequisito)(item["gerenciador"])
    if caminho is None:
        return pre
    conferido = (verificar or integridade.verificar)(item)
    if not conferido.ok:
        return conferido.mensagem
    from jarvis.pc.actions import Action

    acao = store.save(Action("instalar_mcp", {"id": item["id"], "versao": item["versao"]}, _descricao(item, pre) + "\nConferência agora: " + conferido.mensagem,
                             "pedido do usuário: ferramentas para o Jarvis"))
    return "Preparei o cartão. Leia as permissões e os riscos e aprove só se concordar:\n" + acao.descricao


def propor_remover(termo: str, store, desativar: bool = False) -> str:
    item = catalogo.achar(termo)
    reg = instalados.registro_de(item["id"]) if item else None
    if item is None or reg is None:
        return "Essa ferramenta não está instalada.\n" + instalados.resumo()
    from jarvis.pc.actions import Action

    verbo = "Desativar" if desativar else "Remover"
    acao = store.save(Action("remover_mcp", {"id": item["id"], "desativar": bool(desativar)},
                             f"{verbo} a ferramenta externa “{item['nome']}” (v{reg.get('versao')}). Ela sai da configuração do Claude CLI na próxima conversa."
                             + ("" if desativar else " O pacote baixado pelo npx/uvx fica no cache do seu usuário (a Jarvis não apaga fora da própria pasta)."),
                             "pedido do usuário"))
    return "Preparei o cartão:\n" + acao.descricao


def _regravar_config() -> None:
    from jarvis import brains

    brains.write_mcp_config()  # o Claude CLI persistente percebe a mudança e reinicia a sessão (ver claude_session)


def executar(action, verificar=None, testar=None, achar_prereq=None) -> str:
    """Chamado só depois do Aprovar. Levanta ValueError com mensagem clara se algo não confere."""
    p = action.params
    item = next((i for i in catalogo.itens() if i["id"] == p.get("id")), None)
    if item is None:
        raise ValueError("essa ferramenta não está mais no catálogo")
    if action.kind == "remover_mcp":
        if not instalados.remover(item["id"], bool(p.get("desativar"))):
            raise ValueError("a ferramenta não estava instalada")
        _regravar_config()
        log.info("mcp %s %s", item["id"], "desativado" if p.get("desativar") else "removido")
        return f"“{item['nome']}” foi {'desativada' if p.get('desativar') else 'removida'}. Vale na próxima conversa com o Claude."
    if action.kind != "instalar_mcp":
        raise ValueError(f"cartão desconhecido: {action.kind}")
    if p.get("versao") != item["versao"]:
        raise ValueError("o catálogo mudou desde que o cartão foi criado; peça a instalação de novo")
    caminho, pre = (achar_prereq or saude.prerequisito)(item["gerenciador"])
    if caminho is None:
        raise ValueError(pre)
    conferido = (verificar or integridade.verificar)(item)
    if not conferido.ok:
        raise ValueError(conferido.mensagem)
    programa, argumentos, env = catalogo.comando(item, str(data_dir()))
    teste = (testar or saude.testar)(programa, argumentos, env)
    if not teste.ok:
        raise ValueError(f"o teste de saúde falhou: {teste.mensagem}. Nada foi ligado.")
    instalados.registrar(item, teste.ferramentas)
    _regravar_config()
    log.info("mcp %s %s instalado", item["id"], item["versao"])
    return (f"“{item['nome']}” instalada e testada ({teste.mensagem}: {', '.join(teste.ferramentas[:6])}). "
            "Vale a partir da próxima conversa com o Claude CLI.")

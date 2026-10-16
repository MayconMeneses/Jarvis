"""Habilidades do motor próprio (sem IA): memória, perfil, projetos, dashboards e sessões.

Cada função recebe o texto ORIGINAL do usuário (com maiúsculas e acentos, que importam para
nomes, caminhos e valores) e devolve a resposta pronta. Nada aqui chama modelo ou API: são
as mesmas funções que o Claude usa pelas ferramentas MCP, chamadas direto por regras.
"""

from __future__ import annotations

import re
from pathlib import Path

from jarvis import config as config_module
from jarvis import memory_db

# Prefixo opcional: "Jarvis, por favor, ..."
_LEAD = r"^\s*(?:(?:ei|ok|oi|hey)?[\s,]*jarvis[\s,:!.]*)?(?:por favor[\s,]*|pfv[\s,]*)?"
FIELDS = {"stack": "Stack", "nivel": "Nível", "nível": "Nível", "modalidade": "Modalidade",
          "ingles": "Inglês", "inglês": "Inglês", "cidade": "Cidade", "evitar": "Evitar"}


def _grab(pattern: str, text: str) -> re.Match | None:
    return re.search(_LEAD + pattern, text, flags=re.I | re.S)


def _clean_value(value: str) -> str:
    return value.strip().strip('"“”\'').rstrip(".!").strip()


def _title(fact: str) -> str:
    """Título curto a partir do começo do fato (sem IA: as primeiras palavras)."""
    words = re.sub(r"[^\w\s-]", "", fact).split()[:6]
    title = " ".join(words).strip()
    return title[:1].upper() + title[1:] if title else "Anotação"


def remember(text: str, cfg) -> str:
    m = _grab(r"(?:lembr\w*|anot\w*|guard\w*|memoriz\w*)\s+(?:de\s+)?(?:que\s+)?(?P<fato>.+)$", text)
    fact = _clean_value(m["fato"]) if m else ""
    if not fact:
        return "O que você quer que eu lembre? Diga: \"lembre que eu prefiro vagas remotas\"."
    memory_db.open_memory(cfg).remember(_title(fact), fact)
    return f"Anotado na minha memória: {fact}"


def forget_hint() -> str:
    return "Para apagar ou corrigir algo que eu guardei, abra **◈ Memória** no alto da janela."


def recall(text: str, cfg) -> str:
    m = _grab(r"(?:o que voc[eê] (?:sabe|lembra)|busqu\w*|procur\w*|pesquis\w*)\s+(?:na|nas|em)\s+(?:minha\s+)?"
              r"(?:mem[oó]ria|notas)\s*(?:(?:sobre|de|do|da)\s+)?(?P<tema>.*)$", text)
    m = m or _grab(r"o que voc[eê] (?:sabe|lembra)\s+(?:sobre|de|do|da)\s+(?P<tema>.+)$", text)
    topic = _clean_value(m["tema"]) if m else ""
    mem = memory_db.open_memory(cfg)
    if not topic or topic.lower() in {"mim", "eu", "mim?"}:
        index = mem.index_text()
        return ("**O que eu guardei sobre você:**\n" + index) if index else "Ainda não guardei nada sobre você."
    hits = mem.search(topic, 5)
    if not hits:
        return f"Não achei nada sobre \"{topic}\" na minha memória."
    return f"**Na minha memória sobre \"{topic}\":**\n" + "\n".join(f"- {h['nota']}: {h['trecho'][:200]}" for h in hits)


def profile(text: str, cfg) -> str:
    from jarvis.info import jobs

    m = _grab(r"(?:meu|minha)\s+(?P<campo>stack|n[ií]vel|modalidade|ingl[eê]s|cidade)\s*(?:[eé]|[eé]h|s[aã]o|:|=)\s*(?P<valor>.+)$", text)
    campo = m["campo"].lower() if m else ""
    if not m:
        m = _grab(r"(?:quero\s+)?evit\w+\s+(?P<valor>.+)$", text)
        campo = "evitar"
    if not m:
        return "Diga, por exemplo: \"meu nível é pleno\" ou \"minha stack é Python e React\"."
    value = _clean_value(m["valor"])
    name = FIELDS.get(campo, FIELDS.get(re.sub(r"[íì]", "i", campo), "Stack"))
    jobs.update_profile(memory_db.open_memory(cfg), name, value)
    if name == "Cidade":
        cfg.city = value
        config_module.save(cfg)
    return f"Perfil atualizado: {name} = {value}."


def projects_list(cfg) -> str:
    if not cfg.projetos:
        return "Nenhum projeto cadastrado. Diga: \"meu projeto Loja fica em C:\\caminho\\da\\pasta\"."
    return "**Seus projetos:**\n" + "\n".join(f"- {name}: {folder}" for name, folder in cfg.projetos.items())


def project_note(text: str, cfg) -> str:
    from jarvis.dev import projects

    m = _grab(r"anot\w*\s+(?:no|na|ao|em)\s+(?:projeto\s+)?(?P<projeto>.+?)\s+que\s+(?P<info>.+)$", text)
    if not m:
        return "Diga: \"anota no projeto Loja que decidimos usar Postgres\"."
    projects.add_info(cfg, memory_db.open_memory(cfg), m["projeto"].strip(), _clean_value(m["info"]))
    return f"Anotado na ficha do projeto {m['projeto'].strip()}."


def project_card(text: str, cfg) -> str:
    from jarvis.dev import projects

    m = _grab(r"(?:ficha|anota[cç][oõ]es)\s+(?:do\s+)?projeto\s+(?P<projeto>.+)$", text)
    if not m:
        return "Diga: \"ficha do projeto Loja\"."
    info = projects.read_info(cfg, memory_db.open_memory(cfg), m["projeto"].strip())
    return info or "Esse projeto ainda não tem ficha. Diga: \"anota no projeto X que ...\"."


def dashboard(text: str) -> str:
    from jarvis import dashboard as dash

    m = _grab(r"(?:cri\w*|fa[cç]\w*|faz|ger\w*|mont\w*)\s+(?:um\s+|o\s+)?dashboard\s+(?:d[eoa]s?|com|para|pra)\s+(?P<arquivo>.+)$", text)
    path = _clean_value(m["arquivo"]) if m else ""
    if not path:
        return "Diga o arquivo: \"crie um dashboard de C:\\caminho\\vendas.xlsx\" (ou use o botão de gráfico da janela)."
    out = dash.build(path)
    dash.open_in_browser(out)
    return f"Abri o dashboard de {Path(path).name} no navegador. Ele ficou salvo em {out}."


def sessions_waiting() -> str:
    from jarvis.dev import sessions

    found = sessions.SessionReader().sessions()
    waiting = [s for s in found if s.esperando]
    if not waiting:
        return f"Nenhuma sessão do Claude Code está esperando você agora ({len(found)} aberta(s))."
    return "**Sessões esperando você:**\n" + "\n".join(f"- {s.frase()}" for s in waiting)

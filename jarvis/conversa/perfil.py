"""Perfil do usuário: quem ele é, projetos, preferências, tom e metas. Persistente, editável e sempre com aprovação.

Fica na nota "Perfil do Usuário" da memória (SQLite). Campos que o usuário não definiu são DEDUZIDOS do que a Jarvis já
sabe (nome, cidade, "Perfil Profissional", projetos cadastrados, notas de metas e preferências). Mudar ou apagar um campo
cria um cartão de aprovação (ação "atualizar_perfil"); nada é gravado sem o Aprovar, e dado sensível é recusado.
"""

from __future__ import annotations

import re

from jarvis.conversa import privacidade
from jarvis.conversa.reescrita import dobrar

REF = "Perfil do Usuário"
CAMPOS = {"quem": "Quem sou", "projetos": "Projetos", "preferencias": "Preferências", "tom": "Tom de conversa", "metas": "Metas"}
ALIASES = {"quem sou": "quem", "quem eu sou": "quem", "sobre mim": "quem", "projeto": "projetos", "projetos": "projetos",
           "preferencia": "preferencias", "preferencias": "preferencias", "gosto": "preferencias", "tom": "tom", "jeito": "tom",
           "tom de conversa": "tom", "meta": "metas", "metas": "metas", "objetivo": "metas", "objetivos": "metas"}
MAX_VALOR = 300
_CONTROLE = re.compile(r"[\x00-\x1f\x7f]|\[\[|\]\]")
_LINHA = re.compile(r"^-\s*(?P<nome>[^:]{2,30}):\s*(?P<valor>.+)$")


def campo_de(texto: str) -> str | None:
    baixo = dobrar(texto).strip()
    return ALIASES.get(baixo) or (baixo if baixo in CAMPOS else None)


def explicito(mem) -> dict[str, str]:
    """Campos definidos pelo usuário (aprovados antes)."""
    corpo = mem.get(REF) if mem is not None else None
    achados: dict[str, str] = {}
    por_nome = {v: k for k, v in CAMPOS.items()}
    for linha in (corpo or "").splitlines():
        m = _LINHA.match(linha.strip())
        if m and m["nome"].strip() in por_nome:
            achados[por_nome[m["nome"].strip()]] = m["valor"].strip()
    return achados


def _pares_perfil_profissional(mem) -> dict[str, str]:
    pares: dict[str, str] = {}
    for linha in (mem.get("Perfil Profissional") or "").splitlines():
        m = re.match(r"^[-*]?\s*\**(Stack|Nível|Cidade|Modalidade|Inglês)\**\s*:\s*\**\s*(.+)$", linha.strip())
        if m and m[2].strip().strip("*"):
            pares[m[1]] = m[2].strip().strip("*")
    return pares


def deduzido(mem, cfg) -> dict[str, str]:
    """O que dá para saber sem perguntar: nome, cidade, perfil profissional, projetos, metas e preferências já guardados."""
    valores: dict[str, str] = {}
    quem = [getattr(cfg, "user_name", "") or "Maycon"]
    if getattr(cfg, "city", ""):
        quem.append(f"mora em {cfg.city}")
    try:
        pp = _pares_perfil_profissional(mem)
        if pp.get("Stack"):
            quem.append(f"stack {pp['Stack']}")
        if pp.get("Nível"):
            quem.append(f"nível {pp['Nível']}")
        nomes = list(getattr(cfg, "projetos", {}) or {})
        nomes += [n["ref"].split("/")[1] for n in mem.list_notes("Projetos/", 40) if n["ref"].count("/") >= 2]
        projetos = list(dict.fromkeys(nomes))[:8]
        if projetos:
            valores["projetos"] = ", ".join(projetos)
        metas = [n["resumo"] or n["ref"].split("/")[-1] for n in mem.list_notes("Metas/", 5)]
        if any(metas):
            valores["metas"] = "; ".join(m for m in metas if m)[:MAX_VALOR]
        prefs = [t + ": " + r for t, r in mem.memories() if re.search(r"prefer|gosto|estilo|tom", t, re.I)][:4]
        if prefs:
            valores["preferencias"] = "; ".join(prefs)[:MAX_VALOR]
    except Exception:  # a memória nunca derruba a conversa
        pass
    valores["quem"] = ", ".join(quem)
    return valores


def compilar(mem, cfg) -> dict[str, tuple[str, str]]:
    """campo -> (valor, origem), com origem 'definido' ou 'deduzido'. O definido pelo usuário sempre vence."""
    saida = {c: (v, "deduzido") for c, v in deduzido(mem, cfg).items()}
    if mem is not None:
        saida.update({c: (v, "definido") for c, v in explicito(mem).items()})
    return saida


def para_prompt(mem, cfg, limite: int = 700) -> str:
    perfil = compilar(mem, cfg)
    return "\n".join(f"- {CAMPOS[c]}: {perfil[c][0]}" for c in CAMPOS if c in perfil)[:limite]


def lembrancas(mem) -> str:
    """O que o usuário pediu para lembrar (índice da memória), sem dado sensível."""
    try:
        linhas = (mem.index_text() if mem is not None else "").splitlines()
    except Exception:  # a memória nunca derruba a conversa
        return ""
    return "\n".join(l for l in linhas if l.strip() and not privacidade.sensivel(l))


def vazio(mem, cfg) -> bool:
    """Nada além do nome: sem campos definidos, sem deduções e sem lembranças."""
    return set(compilar(mem, cfg)) <= {"quem"} and not lembrancas(mem)


def para_usuario(mem, cfg) -> str:
    perfil = compilar(mem, cfg)
    linhas = []
    for c, nome in CAMPOS.items():
        valor, origem = perfil.get(c, ("(não sei ainda)", ""))
        marca = " _(você definiu)_" if origem == "definido" else (" _(deduzi das suas notas)_" if origem else "")
        linhas.append(f"- **{nome}:** {valor}{marca}")
    guardado = lembrancas(mem)
    extra = ("\n\n**O que você me pediu para lembrar:**\n" + guardado) if guardado else (
        "\n\nAinda não guardei nada que você tenha me pedido para lembrar." if vazio(mem, cfg) else "")
    return ("**O que eu sei sobre você:**\n" + "\n".join(linhas) + extra
            + "\n\nPara mudar: “atualize meu perfil: tom = direto e curto” (eu mostro um cartão e você aprova). "
              "Para apagar um campo: “apague tom do meu perfil”. Não guardo senhas, documentos, valores em dinheiro nem saúde.")


def validar(campo: str, valor: str) -> tuple[str, str]:
    if campo not in CAMPOS:
        raise ValueError("campo desconhecido (use: " + ", ".join(CAMPOS.values()) + ")")
    valor = re.sub(r"\s+", " ", str(valor)).strip()
    if not valor or len(valor) > MAX_VALOR:
        raise ValueError(f"o valor precisa ter de 1 a {MAX_VALOR} caracteres")
    if _CONTROLE.search(valor):
        raise ValueError("valor com caracteres não permitidos")
    if privacidade.sensivel(valor):
        raise ValueError("isso parece dado sensível (senha, documento, valor em dinheiro ou saúde); não guardo no perfil")
    return campo, valor


def propor(store, mem, campo: str, valor: str):
    """Cartão 'Atualizar seu perfil?'. Não grava nada."""
    from jarvis.pc import actions

    campo, valor = validar(campo, valor)
    antes = explicito(mem).get(campo)
    desc = f"Atualizar seu perfil? {CAMPOS[campo]}: {valor}" + (f"\n(antes: {antes})" if antes else "")
    return store.save(actions.Action("atualizar_perfil", {"campo": campo, "valor": valor}, desc,
                                     "o perfil ajuda a Jarvis a responder do seu jeito; nada é gravado se você recusar"))


def propor_apagar(store, mem, campo: str):
    from jarvis.pc import actions

    atual = explicito(mem)
    if campo not in atual:
        raise ValueError("esse campo não está definido no seu perfil")
    return store.save(actions.Action("atualizar_perfil", {"campo": campo, "valor": ""},
                                     f"Apagar do seu perfil: {CAMPOS[campo]} (hoje: {atual[campo]})",
                                     "nada é apagado se você recusar"))


def executar(params: dict) -> str:
    """Chamado só depois do Aprovar: valida de novo e grava (valor vazio apaga o campo)."""
    from jarvis import config, memory_db

    campo = str(params.get("campo", ""))
    mem = memory_db.open_memory(config.load())
    atual = explicito(mem)
    if str(params.get("valor", "")).strip() == "":
        if campo not in CAMPOS:
            raise ValueError("campo desconhecido")
        atual.pop(campo, None)
        msg = f"Apaguei “{CAMPOS[campo]}” do seu perfil."
    else:
        campo, valor = validar(campo, params.get("valor", ""))
        atual[campo] = valor
        msg = f"Perfil atualizado: {CAMPOS[campo]} = {valor}."
    corpo = "# Perfil do Usuário\n\n" + "\n".join(f"- {CAMPOS[c]}: {v}" for c, v in atual.items() if c in CAMPOS) + "\n"
    mem.put(REF, corpo, "perfil", "Perfil do usuário (definido por ele)", REF)
    return msg

"""Cérebro generativo local no motor próprio: instalar (por cartão), ver o estado e criar sistemas pensando."""

from __future__ import annotations

import re

from jarvis.llm import catalogo, tarefas
from jarvis.local import dev_skills

_PASTA = re.compile(r"\b(?:em|na pasta|dentro de)\s+(?P<p>[A-Za-z]:\\[^:]+?)\s*(?::|$)", re.I)


def _modelo(texto: str) -> str:
    baixo = texto.lower()
    return "qwen2.5-3b" if re.search(r"\b3\s*b\b|maior|melhor", baixo) else catalogo.PADRAO


def instalar(texto: str, cfg) -> str:
    from jarvis.pc import actions

    item = catalogo.modelo(_modelo(texto))
    est = catalogo.estado(item.id, cfg.llm_endpoint)
    if est["pronto"]:
        cfg.llm_local = True
        cfg.llm_modelo = item.id
        from jarvis import config

        config.save(cfg)
        return f"O cérebro local ({item.nome}) já está instalado e agora está ligado."
    acao = actions.ActionStore().save(actions.Action(
        "instalar_llm", {"modelo": item.id},
        f"Baixar o motor llama.cpp (cerca de {catalogo.MOTOR_MB} MB, de github.com/ggml-org/llama.cpp) e o modelo {item.nome} "
        f"(cerca de {item.mb} MB, de huggingface.co/{item.repo}) para a pasta da Jarvis em AppData/Local. "
        f"Usa cerca de {item.ram_gb:g} GB de memória enquanto responde. {item.descricao}",
        "pedido do usuário: ter uma IA generativa própria, sem depender de ninguém"))
    return "Preparei a instalação. Confira e aprove o cartão abaixo para eu baixar:\n" + acao.descricao


def status(texto: str, cfg) -> str:
    if re.search(r"\b(desliga\w*|desativ\w*)\b", texto.lower()):
        from jarvis import config

        cfg.llm_local = False
        config.save(cfg)
        return "Cérebro local desligado. Os outros cérebros e o motor próprio continuam."
    return tarefas.resumo(cfg)


def criar(texto: str, cfg) -> str:
    est = catalogo.estado(cfg.llm_modelo, cfg.llm_endpoint)
    if not (cfg.llm_local and est["pronto"]):
        return "Para criar pensando eu preciso do cérebro local. Peça: \"instalar cérebro local\"."
    pasta = _PASTA.search(texto)
    nome = dev_skills._name(texto[:pasta.start()] if pasta else texto)
    if not nome or not pasta:
        return ("Diga o nome e a pasta, por exemplo: \"crie com a IA local um sistema chamado Agenda em C:\\Projetos: "
                "uma agenda de contatos em Python com testes\".")
    descricao = texto.split(":", 2)[-1].strip() if texto.count(":") >= 2 else texto.strip()
    if not tarefas.criar(nome, pasta["p"], descricao):
        return "Já estou criando um sistema. Pergunte \"status do cérebro local\" para acompanhar."
    return (f"Comecei a pensar no sistema **{nome}** com o modelo local. É lento no seu PC (de 10 a 40 minutos); "
            "quando terminar, um cartão com os arquivos vai esperar a sua aprovação. Pergunte \"status do cérebro local\".")

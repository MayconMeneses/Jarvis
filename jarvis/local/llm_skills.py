"""Cérebro generativo local no motor próprio: instalar (por cartão), ver o estado e criar sistemas pensando."""

from __future__ import annotations

import re

from jarvis.llm import catalogo, tarefas
from jarvis.local import dev_skills

_PASTA = re.compile(r"\b(?:em|na pasta|dentro de)\s+(?P<p>[A-Za-z]:\\[^:]+?)\s*(?::|$)", re.I)


def _modelo(texto: str) -> str:
    """O pedido escolhe ("7b", "3b", "maior"); sem escolha, o melhor para este aparelho (mais memória, modelo maior)."""
    from jarvis.llm import perfil

    baixo = texto.lower()
    if re.search(r"\b7\s*b\b", baixo):
        return "qwen2.5-coder-7b"
    if re.search(r"\b3\s*b\b|maior|melhor", baixo):
        return "qwen2.5-coder-3b" if perfil.recomendado() == "qwen2.5-coder-1.5b" else perfil.recomendado()
    return perfil.recomendado()


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


def avaliar(texto: str, cfg) -> str:
    """Roda a régua de tarefas no modelo local (leva alguns minutos) e guarda a nota para comparar com a próxima vez."""
    from jarvis import memory_db
    from jarvis.llm import avaliar as regua
    from jarvis.llm.cerebro import conversa_local

    if not (cfg.llm_local and catalogo.estado(cfg.llm_modelo, cfg.llm_endpoint)["pronto"]):
        return 'Para avaliar eu preciso do cérebro local ligado. Peça: "instalar cérebro local".'
    conversa = conversa_local(cfg)
    try:
        r = regua.avaliar(conversa)
    except RuntimeError as exc:
        return str(exc)
    finally:
        conversa.servidor.parar()
    nome = catalogo.modelo(cfg.llm_modelo).nome
    return regua.relatorio(nome, r) + regua.registrar(memory_db.open_memory(cfg), nome, r)


def aprender(texto: str, cfg) -> str:
    from jarvis import aprender as web

    return web.aprender(texto, cfg)


def autonomo(texto: str, cfg) -> str | None:
    """"o que você aprendeu" mostra o que ela estudou sozinha; "ligar/desligar aprendizado automático" muda a configuração."""
    import re

    from jarvis import config, memory_db
    from jarvis.autonomo import estudar

    baixo = texto.lower()
    if re.search(r"aprendeu|estudou", baixo):
        return estudar.resumo(memory_db.open_memory(cfg))
    if re.search(r"aprendizado|sozinha", baixo):
        ligar = not re.search(r"desl|desat|pare|p[aá]ra", baixo)
        cfg.autonomo = ligar
        config.save(cfg)
        return ("Ligado: com o PC parado, estudo até %d assuntos por dia sobre o que você mais pergunta. Diga \"o que você aprendeu\" para ver." % cfg.autonomo_max_por_dia
                if ligar else "Desligado: não estudo mais nada sozinha.")
    return None


def status(texto: str, cfg) -> str:
    achado = autonomo(texto, cfg)
    if achado is not None:
        return achado
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

"""Escolha do cérebro local: lista com avisos de espaço, memória e velocidade; troca; volta ao modelo antigo.

Instalar um modelo NUNCA apaga o anterior: o arquivo antigo continua na pasta e "voltar" é só mudar a escolha.
"""

from __future__ import annotations

import shutil

from jarvis import config
from jarvis.llm import catalogo, perfil


def _aviso(item: catalogo.Modelo, estado: dict, ram_total: float, livre_gb: float) -> str:
    partes = []
    if not estado["arquivo"]:
        partes.append(f"download de cerca de {item.mb / 1024:.1f} GB (precisa de espaço livre; hoje há {livre_gb:.0f} GB)")
    partes.append(f"usa cerca de {item.ram_gb:g} GB de memória enquanto responde")
    if item.tps:
        partes.append(f"neste tipo de PC fala ~{item.tps * 0.75:.0f} palavras por segundo ({item.tps:g} tokens/s medidos)")
    if item.ram_gb > ram_total - 3:
        partes.append("ATENÇÃO: pode faltar memória; feche outros programas ou prefira um modelo menor")
    if item.licenca.startswith("Qwen Research"):
        partes.append("licença só para uso não comercial")
    return "; ".join(partes) + "."


def listar(cfg) -> list[dict]:
    """Todos os modelos do catálogo, com o estado de instalação e o aviso para o usuário."""
    p = perfil.medir()
    try:
        livre = shutil.disk_usage(catalogo.raiz().anchor or ".").free / 1024**3
    except OSError:
        livre = 0.0
    saida = []
    for item in catalogo.MODELOS.values():
        est = catalogo.estado(item.id, cfg.llm_endpoint)
        saida.append({"id": item.id, "nome": item.nome, "descricao": item.descricao, "mb": item.mb, "ram_gb": item.ram_gb,
                      "instalado": est["arquivo"], "ativo": item.id == cfg.llm_modelo, "conversa": item.conversa,
                      "recomendado": item.id == perfil.recomendado(p["ram_gb"], conversa=True),
                      "aviso": _aviso(item, est, p["ram_gb"], livre)})
    return saida


def trocar(cfg, id_: str) -> dict:
    """Usa um modelo já instalado. Se faltar o arquivo, não muda nada: o download é por cartão aprovado."""
    if id_ not in catalogo.MODELOS:
        return {"ok": False, "mensagem": f"Não conheço o modelo {id_}."}
    item = catalogo.MODELOS[id_]
    if catalogo.caminho_modelo(id_) is None:
        return {"ok": False, "instalar": True, "mensagem": f"O {item.nome} ainda não está instalado. Peça: \"instalar cérebro local {id_}\" e aprove o cartão."}
    anterior = cfg.llm_modelo
    cfg.llm_modelo = id_
    config.save(cfg)
    volta = f" Para voltar ao anterior ({catalogo.MODELOS[anterior].nome}), escolha-o na lista." if anterior in catalogo.MODELOS and anterior != id_ else ""
    return {"ok": True, "modelo": id_, "mensagem": f"Agora o cérebro local usa o {item.nome}.{volta}"}


def voltar_antigo(cfg) -> dict:
    """Volta ao modelo padrão original (o pequeno e rápido), que continua instalado."""
    return trocar(cfg, catalogo.PADRAO)

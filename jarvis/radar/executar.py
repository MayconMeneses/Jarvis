"""Orquestra o Radar: coleta → filtro → dedup → pontuação → curadoria → resumo → boletim → áudio → memória.

Todo I/O (rede, voz, relógio) entra por parâmetro, então o fluxo inteiro roda nos testes sem internet.
Falha de uma fonte não derruba o resto; sem internet em nenhuma fonte avisa em vez de gerar boletim vazio.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from jarvis import files
from jarvis.radar import catalogo, curadoria, dedup, feed_parse, narrar as voz_mod, pontuacao, rede, render, resumo, roteiro
from jarvis.radar.ajustes import RadarConfig
from jarvis.radar.historico import Historico
from jarvis.radar.modelos import Boletim, Item

RETENCAO_AUDIO_DIAS = 30


def pasta_do_radar(cfg: RadarConfig) -> Path:
    return Path(cfg.pasta) if cfg.pasta else files.output_dir() / "Radar"


def _coletar(fontes, baixar, progresso):
    def uma(fonte):
        try:
            dados, _ = baixar(fonte.feed)
            return fonte, feed_parse.parse(dados, fonte.nome, fonte.nota, fonte.tipo), None
        except Exception as exc:  # fonte fora do ar: vai para o log, o resto continua
            return fonte, [], f"{fonte.nome}: {type(exc).__name__}"

    with ThreadPoolExecutor(max_workers=min(6, len(fontes) or 1)) as pool:
        resultados = list(pool.map(uma, fontes))
    artigos = [a for _, lista, _ in resultados for a in lista]
    falhas = [erro for _, _, erro in resultados if erro]
    return artigos, falhas, len(resultados) - len(falhas)


def _pasta_livre(base: Path, nome: str) -> Path:
    """AAAA-MM-DD, depois "AAAA-MM-DD (2)"...: nunca sobrescreve um boletim que já existe."""
    pasta, n = base / nome, 2
    while pasta.exists():
        pasta = base / f"{nome} ({n})"
        n += 1
    pasta.mkdir(parents=True)
    return pasta


def limpar_audios_antigos(base: Path, dias: int = RETENCAO_AUDIO_DIAS, agora: float | None = None) -> int:
    corte, apagados = (agora if agora is not None else time.time()) - dias * 86400, 0
    for wav in base.glob("*/boletim.wav") if base.exists() else []:
        if wav.stat().st_mtime < corte:
            wav.unlink(missing_ok=True)
            apagados += 1
    return apagados


def executar(cfg: RadarConfig, hist: Historico, mem=None, agora: datetime | None = None, baixar=rede.baixar,
             ler_pagina=resumo.ler_pagina, narrar=voz_mod.narrar, progresso=None, atrasado: bool = False,
             melhorar=None, avisos_iniciais: list[str] | None = None) -> dict:
    """Roda o Radar uma vez. Devolve {ok, ...} com os caminhos, números e avisos (ou {ok: False, erro})."""
    agora = agora or datetime.now()
    inicio, dia = time.time(), agora.strftime("%Y-%m-%d")
    dito = progresso or (lambda texto: None)
    if not cfg.nicho.strip():
        return {"ok": False, "erro": "Defina o nicho do Radar primeiro (ex.: \"radar nicho inteligência artificial\")."}
    if not hist.fontes(so_ativas=True):
        catalogo.semear(hist, cfg.nicho)
    fontes = hist.fontes(so_ativas=True)
    if not fontes:
        return {"ok": False, "erro": "O Radar não tem fontes ativas. Use \"radar +fonte <endereço>\"."}

    dito(f"Lendo {len(fontes)} fontes…")
    artigos, falhas, funcionaram = _coletar(fontes, baixar, dito)
    if funcionaram == 0:
        hist.registrar_execucao(dia, inicio, 0, 0, 0, falhas, "BLOCKED")
        return {"ok": False, "erro": "Nenhuma fonte respondeu: parece que não há internet. Não gerei boletim vazio.", "falhas": falhas}

    aceitos, descartes = curadoria.filtrar(artigos, cfg.bloqueios, cfg.janela_horas, agora.timestamp())
    novos = [a for a in aceitos if not hist.ja_visto(a)]
    recentes = hist.titulos_recentes(14, agora.timestamp())
    palavras = cfg.palavras_chave or []
    itens = []
    for principal, tambem in dedup.agrupar(novos):
        nota, motivos = pontuacao.pontuar(principal, palavras, cfg.entidades_seguidas, cfg.janela_horas, recentes, agora.timestamp())
        itens.append(Item(principal, nota, motivos, tambem))
    escolhidos = curadoria.escolher(itens, cfg.principais, cfg.radar, cfg.max_por_fonte, cfg.nota_minima)

    dito("Resumindo…")
    avisos = list(avisos_iniciais or [])
    for posicao, item in enumerate(escolhidos):  # os melhores têm a página lida; os outros ficam só no RSS
        texto, paywall = "", False
        if posicao < cfg.ler_artigos:
            texto, estado = ler_pagina(item.artigo.link)
            if estado == "robots":
                avisos.append(f"{item.artigo.fonte}: o site pede (robots.txt) para não ler a página; resumo só do RSS")
            paywall = estado == "lida" and resumo.parece_paywall(texto, item.artigo.resumo)
        resumo.resumir(item, texto, paywall)

    boletim = Boletim(dia, cfg.nicho, escolhidos, varridos=len(artigos), falhas=falhas, avisos=avisos, atrasado=atrasado)
    if falhas:
        boletim.avisos.append(f"{len(falhas)} fonte(s) indisponível(is) hoje")
    if melhorar is not None and cfg.usar_ia:
        melhorar(boletim)  # camada opcional de IA (sempre degrada para o resumo extrativo)

    base = pasta_do_radar(cfg)
    pasta = _pasta_livre(base, dia)
    (pasta / "boletim.md").write_text(render.markdown(boletim), encoding="utf-8")
    (pasta / "boletim.html").write_text(render.pagina(boletim), encoding="utf-8")
    plano = roteiro.montar(boletim, cfg.max_palavras, agora)
    (pasta / "roteiro-audio.txt").write_text(plano["texto"], encoding="utf-8")
    resultado = {"ok": True, "dia": dia, "pasta": str(pasta), "md": str(pasta / "boletim.md"), "html": str(pasta / "boletim.html"),
                 "audio": None, "duracao_s": 0.0, "itens": len(escolhidos), "varridos": len(artigos), "novos": len(novos),
                 "falhas": falhas, "avisos": boletim.avisos, "descartes": descartes, "cortados_no_audio": len(plano["cortados"]),
                 "boletim": boletim}
    if cfg.audio and escolhidos:
        dito("Gerando o áudio…")
        try:
            saida = narrar(plano["texto"], pasta / "boletim.wav")
            resultado.update(audio=saida["caminho"], duracao_s=saida["duracao_s"], motor_de_voz=saida["motor"])
        except Exception as exc:  # sem áudio, o boletim escrito continua valendo
            resultado["avisos"].append(f"não consegui gerar o áudio ({type(exc).__name__})")

    hist.registrar(aceitos, {dedup.id_do_artigo(i.artigo) for i in escolhidos}, agora.timestamp())
    hist.registrar_execucao(dia, inicio, len(artigos), len(novos), len(escolhidos), falhas, "PASS" if escolhidos else "SEM_ITENS")
    hist.limpar(agora=agora.timestamp())
    limpar_audios_antigos(base, agora=agora.timestamp())
    if mem is not None:
        try:
            mem.put(f"Radar/{dia}", render.markdown(boletim), "relatorio", f"{len(escolhidos)} notícias sobre {cfg.nicho}")
            mem.set_meta(f"radar:{dia}", "1")
        except Exception:
            resultado["avisos"].append("não consegui guardar o boletim na memória")
    return resultado

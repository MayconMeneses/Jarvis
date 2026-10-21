"""O que os comandos do Radar fazem (voz, texto e ferramentas de leitura do MCP). Tudo devolve texto pronto para mostrar.

Não há ferramenta que adicione fonte ou mude o nicho para a IA: isso só acontece por comando do próprio usuário.
"""

from __future__ import annotations

import re
import threading
import webbrowser
from contextlib import contextmanager
from datetime import date, timedelta

from jarvis import config, keys, memory_db
from jarvis.radar import catalogo, descobrir, executar, reproduzir
from jarvis.radar.agendador import RadarAgendador, hora_de
from jarvis.radar.historico import Historico

_registrado: RadarAgendador | None = None


def registrar(agendador: RadarAgendador | None) -> None:
    """A janela registra o agendador dela, para o aviso "Radar pronto" chegar na tela."""
    global _registrado
    _registrado = agendador


def rodando(cfg) -> bool:
    return _agendador(cfg)._trava.locked()


def _agendador(cfg) -> RadarAgendador:
    return _registrado or RadarAgendador(config.load, memory_db.open_memory(cfg), lambda texto: None)


@contextmanager
def _hist(hist: Historico | None = None):
    h = hist or Historico()
    try:
        yield h
    finally:
        if hist is None:
            h.fechar()


def _salvar(cfg) -> None:
    config.save(cfg)


def rodar(cfg, so_texto: bool = False) -> str:
    if not cfg.radar.nicho.strip():
        return "Defina o nicho primeiro: \"radar nicho inteligência artificial\"."
    agendador = _agendador(cfg)
    if agendador._trava.locked():
        return "O Radar já está rodando; aviso quando terminar."
    threading.Thread(target=lambda: agendador.executar(sem_audio=so_texto), daemon=True, name="jarvis-radar-manual").start()
    return "📰 O Radar começou (leva de 1 a 3 minutos). Avisarei quando o boletim estiver pronto."


def status(cfg, hist: Historico | None = None) -> str:
    r = cfg.radar
    mem = memory_db.open_memory(cfg)
    with _hist(hist) as h:
        ultima, fontes = h.ultima_execucao(), h.fontes()
    linhas = [f"**Radar** — nicho: {r.nicho or '(não definido)'} · {'ligado' if r.ativo else 'desligado'} · "
              f"{r.hora} {'em dias úteis' if r.dias_uteis else 'todos os dias'} · IA: {'ligada' if r.usar_ia else 'desligada'} · "
              f"áudio: {'sim' if r.audio else 'não'}",
              f"Fontes ativas: {sum(f.ativa for f in fontes)} de {len(fontes)}"]
    if ultima:
        linhas.append(f"Última execução: {ultima['dia']} — {ultima['escolhidos']} itens de {ultima['varridos']} varridos "
                      f"({ultima['novos']} novos) · resultado {ultima['resultado']}")
        if ultima["falhas"]:
            linhas.append(f"Fontes que falharam: {ultima['falhas']}")
    else:
        linhas.append("Ainda não rodou. Diga \"radar\" para gerar o primeiro boletim.")
    seguidas = int(mem.meta("radar:falhas_seguidas") or 0)
    if seguidas:
        linhas.append(f"⚠ Falhou em {seguidas} dia(s) seguido(s).")
    return "\n".join(linhas)


def fontes_texto(hist: Historico | None = None) -> str:
    with _hist(hist) as h:
        fontes = h.fontes()
    if not fontes:
        return "O Radar ainda não tem fontes. Diga \"radar nicho <assunto>\" para sugerir, ou \"radar +fonte <endereço>\"."
    return "**Fontes do Radar:**\n" + "\n".join(
        f"- {'✓' if f.ativa else '✗'} {f.nome} ({f.tipo}, {f.idioma}) nota {f.nota:g}{'' if f.medida else ' [credibilidade não medida]'} — {f.feed}"
        for f in fontes)


def adicionar(url: str, cfg, hist: Historico | None = None, **kw) -> str:
    url = url.strip()
    if not url:
        return "Diga o endereço: \"radar +fonte https://exemplo.com\"."
    with _hist(hist) as h:
        r = descobrir.adicionar(url, h, cfg.radar.palavras_chave, **kw)
    if not r["ok"]:
        return f"Não adicionei: {r['motivo']}."
    aviso = " (a credibilidade é um palpite; você pode ajustar a nota)" if r["nao_medida"] else ""
    return (f"Fonte **{r['nome']}** adicionada: nota {r['nota']:g}{aviso}. Feed: {r['feed']}\n"
            f"Últimos títulos: " + " · ".join(r["amostra"]))


def remover(nome: str, hist: Historico | None = None) -> str:
    with _hist(hist) as h:
        return f"Fonte **{nome.strip()}** desativada (o histórico fica guardado)." if h.ativar(nome.strip(), False) else f"Não achei a fonte \"{nome.strip()}\". Veja \"radar fontes\"."


def definir_nicho(texto: str, cfg, hist: Historico | None = None) -> str:
    from jarvis.local import websearch

    texto = " ".join(texto.split())[:120]
    if not texto:
        return "Diga o nicho: \"radar nicho inteligência artificial na saúde\"."
    cfg.radar.nicho = texto
    cfg.radar.palavras_chave = list(dict.fromkeys(websearch.keywords(texto)))[:10]
    _salvar(cfg)
    with _hist(hist) as h:
        novas = catalogo.semear(h, texto)
    return (f"Nicho definido: **{texto}**. Palavras-chave que vou procurar: {', '.join(cfg.radar.palavras_chave) or '(nenhuma)'}.\n"
            f"{novas} fonte(s) sugerida(s) do catálogo. Diga \"radar fontes\" para ver, \"radar ligar\" para agendar "
            f"({cfg.radar.hora}) ou \"radar\" para gerar agora.")


def ligar(cfg, ativo: bool) -> str:
    if ativo and not cfg.radar.nicho.strip():
        return "Defina o nicho antes de ligar: \"radar nicho inteligência artificial\"."
    cfg.radar.ativo = ativo
    _salvar(cfg)
    return (f"Radar ligado: todo {'dia útil' if cfg.radar.dias_uteis else 'dia'} a partir das {cfg.radar.hora}, enquanto a Jarvis estiver aberta."
            if ativo else "Radar desligado (as fontes e o histórico ficam guardados).")


def definir_hora(texto: str, cfg) -> str:
    alvo = re.search(r"\d{1,2}(?::\d{2})?", texto)
    if not alvo:
        return "Diga a hora: \"radar hora 7:30\"."
    h, m = hora_de(alvo.group(0) if ":" in alvo.group(0) else alvo.group(0) + ":00")
    cfg.radar.hora = f"{h:02d}:{m:02d}"
    _salvar(cfg)
    return f"O Radar passa a rodar às {cfg.radar.hora}."


def buscar(tema: str, cfg) -> str:
    from jarvis.local import websearch

    tema = tema.strip()
    if not tema:
        return "Diga o tema: \"radar busca reforma tributária\"."
    return websearch.format_answer(tema, websearch.research(tema, 5, brave_key=keys.get_key("brave")))


def arquivo(termo: str, cfg, hist: Historico | None = None) -> str:
    termo = termo.strip()
    if not termo:
        return "Diga o termo: \"radar arquivo pix\"."
    with _hist(hist) as h:
        titulos = h.buscar(termo, 8)
    notas = [n for n in memory_db.open_memory(cfg).search(termo, 12) if n["nota"].startswith("Radar/")][:5]
    if not titulos and not notas:
        return f"Nada sobre \"{termo}\" no arquivo do Radar."
    linhas = [f"**Arquivo do Radar sobre \"{termo}\":**"] + [f"- {t['titulo']} ({t['fonte']}) {t['link']}" for t in titulos]
    return "\n".join(linhas + [f"- Boletim {n['nota'].removeprefix('Radar/')}: {n['trecho'][:120]}" for n in notas])


def semana(cfg, hoje: date | None = None) -> str:
    """Os títulos dos boletins dos últimos 7 dias (sem IA: lista; o resumão em prosa é só com IA)."""
    mem, hoje = memory_db.open_memory(cfg), hoje or date.today()
    dias = {(hoje - timedelta(days=i)).isoformat() for i in range(7)}
    notas = [n for n in mem.list_notes("Radar/") if n["ref"].removeprefix("Radar/") in dias]
    if not notas:
        return "Não há boletins nos últimos 7 dias."
    linhas = ["**Radar da semana:**"]
    for n in sorted(notas, key=lambda n: n["ref"], reverse=True):
        titulos = re.findall(r"^## \d+\. (.+)$", mem.get(n["ref"]) or "", re.M)
        linhas.append(f"**{n['ref'].removeprefix('Radar/')}**\n" + "\n".join(f"- {t}" for t in titulos))
    return "\n".join(linhas)


def boletim_de_hoje(cfg, limite: int = 6000) -> str:
    texto = memory_db.open_memory(cfg).get(f"Radar/{date.today().isoformat()}")
    return texto[:limite] if texto else "Ainda não há boletim de hoje. Diga \"radar\" para gerar."


def abrir(cfg) -> str:
    pastas = sorted((executar.pasta_do_radar(cfg.radar)).glob("*/boletim.html"), key=lambda p: p.stat().st_mtime) if executar.pasta_do_radar(cfg.radar).exists() else []
    if not pastas:
        return "Ainda não há boletim para abrir. Diga \"radar\" para gerar."
    webbrowser.open(pastas[-1].as_uri())
    return f"Abri o boletim de {pastas[-1].parent.name} no navegador."


def ouvir(cfg, sd=None) -> str:
    arquivo_wav = reproduzir.ultimo_audio(executar.pasta_do_radar(cfg.radar))
    if arquivo_wav is None:
        return "Ainda não há áudio do Radar. Diga \"radar\" para gerar o boletim."
    segundos = reproduzir.tocar(arquivo_wav, sd)
    return f"🔊 Tocando o boletim de {arquivo_wav.parent.name} ({segundos / 60:.1f} min). Diga \"parar radar\" para interromper."


def parar(sd=None) -> str:
    reproduzir.parar(sd)
    return "Parei o áudio do Radar."


AJUDA = ("**Comandos do Radar:** `radar` (gera agora) · `radar texto` (sem áudio) · `ouvir radar` · `parar radar` · `abrir radar` · "
         "`radar fontes` · `radar +fonte <endereço>` · `radar -fonte <nome>` · `radar nicho <assunto>` · `radar busca <tema>` · "
         "`radar semana` · `radar arquivo <termo>` · `radar status` · `radar ligar` / `radar desligar` · `radar hora 7:30`")

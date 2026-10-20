"""Cola entre o chat, o MCP e o armazenamento: importar, configurar, analisar, relatório e comparação."""

from __future__ import annotations

from datetime import datetime

from jarvis.instagram import analise, entrevista, relatorio, rodadas
from jarvis.instagram.armazenar import Armazem
from jarvis.instagram.higiene import epoch
from jarvis.instagram.importar import ler


def configurar(texto: str, arm: Armazem | None = None) -> str:
    arm = arm or Armazem()
    perfil, faltam, avisos = entrevista.aplicar(texto, arm.analise())
    arm.salvar_analise(perfil)
    seguidores = {a: s for a, s in (perfil.get("concorrentes") or {}).items()}
    if perfil.get("proprio"):
        seguidores.setdefault(perfil["proprio"], None)
    arm.definir_perfis(seguidores, perfil.get("proprio", ""))
    linhas = ["Perfil da análise de Instagram atualizado."] + [f"Aviso: {a}" for a in avisos]
    if faltam:
        linhas += ["Ainda preciso de (responda com \"configurar instagram\" e uma linha por campo):"] + [f"- {p}" for p in faltam]
    else:
        linhas.append("Tudo certo. Agora cole os posts: \"importar posts\" e, na linha seguinte, a tabela (perfil, link, data, formato, legenda, likes, comentarios, views...).")
    return "\n".join(linhas)


def importar(texto: str, perfil_padrao: str = "", nova: bool = False, agora: datetime | None = None, arm: Armazem | None = None) -> str:
    arm = arm or Armazem()
    lido = ler(texto, perfil_padrao)
    if not lido["posts"]:
        return "Não importei nenhum post. " + "; ".join(lido["avisos"][:3])
    rodada = arm.rodada_para_importar(agora or datetime.now(), nova)
    novos, atualizados = arm.gravar_posts(rodada, lido["posts"])
    arm.definir_perfis({**{p["perfil"]: None for p in lido["posts"]}, **lido["seguidores"]}, arm.analise().get("proprio", ""))
    linhas = [f"Importei {novos} posts novos e atualizei {atualizados} na rodada {rodada} (de {len({p['perfil'] for p in lido['posts']})} perfis)."]
    linhas += [f"- {a}" for a in lido["avisos"][:6]]
    if len(lido["avisos"]) > 6:
        linhas.append(f"- ... e mais {len(lido['avisos']) - 6} avisos")
    return "\n".join(linhas + ["Diga \"relatório de instagram\" para ver a análise."])


def resultado_da_rodada(rodada_id: int, arm: Armazem, agora: datetime | None = None) -> dict:
    cfg = arm.analise()
    agora_s = epoch((agora or datetime.now()).strftime("%Y-%m-%dT%H:%M:%S"))
    return analise.analisar(arm.posts(rodada_id), arm.seguidores(), cfg.get("pesos"), agora_s, cfg.get("proprio", ""))


def relatorio_atual(agora: datetime | None = None, arm: Armazem | None = None, salvar_em=None) -> str:
    arm = arm or Armazem()
    todas = arm.rodadas()
    if not todas or not todas[-1]["posts"]:
        return "Ainda não tenho posts. Diga \"analisar instagram\" para configurar e \"importar posts\" para colar os dados."
    r = resultado_da_rodada(todas[-1]["id"], arm, agora)
    texto = relatorio.montar(r, arm.analise().get("nicho", ""), str(todas[-1]["id"]))
    if salvar_em is not None:
        salvar_em.save_report(f"Instagram {arm.analise().get('nicho') or 'análise'}", texto, folder="Instagram")
    return texto


def comparar_atual(agora: datetime | None = None, arm: Armazem | None = None) -> str:
    arm = arm or Armazem()
    todas = [r for r in arm.rodadas() if r["posts"]]
    if len(todas) < 2:
        return "Preciso de pelo menos duas rodadas com posts para comparar (importe de novo na próxima semana, com \"importar posts\")."
    a, b = todas[-2], todas[-1]
    return rodadas.texto(rodadas.comparar(resultado_da_rodada(a["id"], arm, agora), resultado_da_rodada(b["id"], arm, agora)), str(a["id"]), str(b["id"]))

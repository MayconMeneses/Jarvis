"""O que o celular pode LER do PC pareado: agenda, e-mails, bom dia e agentes. Somente leitura, sem IA, sem segredos.

Cada função `*_publica` recebe o dado interno e devolve só o que o celular precisa, já limpo:
- título, assunto e remetente são texto de terceiros: sem caracteres de controle, sem links, truncados;
- texto que tenta dar ordens à IA ("suspeito") é OMITIDO (só entra na contagem);
- nunca vai corpo de e-mail, link de agenda (iCal secreto), token, caminho de arquivo nem mensagem de erro técnica.
`montar` liga isso às fontes reais do PC, com um cache curto para o celular não disparar uma busca a cada toque.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from datetime import datetime

from jarvis.mail import rules, triagem

URL = re.compile(r"(?:https?://|ftp://|www\.)\S+", re.IGNORECASE)
OMITIDO = "(texto suspeito omitido)"
AVISO_AGENDA = "Alguma agenda não respondeu; mostrando o que o PC tem."
AVISO_EMAIL = "Alguma conta de e-mail não respondeu."
TTL = 120.0  # segundos


def limpo(texto, limite: int) -> str:
    """Sem controle, sem links, espaços normalizados e truncado."""
    t = "".join(c for c in str(texto or "") if c.isprintable() or c in "\n\t")
    return URL.sub("[link]", re.sub(r"\s+", " ", t)).strip()[:limite]


def _suspeito(*textos) -> bool:
    return any(rules.texto_suspeito(str(t or "")) for t in textos)


def _evento(o) -> dict:
    suspeito = _suspeito(o.titulo, o.local)
    return {"titulo": OMITIDO if suspeito else limpo(o.titulo, 80) or "(sem título)", "inicio": o.inicio.isoformat(),
            "fim": o.fim.isoformat(), "dia_inteiro": bool(o.dia_inteiro), "local": "" if suspeito else limpo(o.local, 60),
            "suspeito": suspeito}


def agenda_publica(semana: dict, proximo, agora: datetime) -> dict:
    """`semana` = resultado de servico.da_semana (7 dias); `proximo` = Ocorrencia ou None."""
    itens = [_evento(o) for o in semana["ocorrencias"]]
    hoje = [e for e, o in zip(itens, semana["ocorrencias"]) if o.inicio.date() == agora.date()]
    return {"gerado": agora.isoformat(), "sem_agendas": bool(semana.get("sem_agendas")), "hoje": hoje, "semana": itens[:60],
            "proximo": _evento(proximo) if proximo is not None else None, "avisos": [AVISO_AGENDA] if semana["avisos"] else []}


def _de(m) -> str:
    nome = re.sub(r"<.*?>", "", m.remetente).strip().strip('"')
    return limpo(nome or m.remetente, 30) or "(remetente)"


def _email(m) -> dict:
    return {"de": _de(m), "assunto": limpo(m.assunto, 70) or "(sem assunto)", "resumo": limpo(m.previa, 90)}


LIMITES = {triagem.ACAO: 10, triagem.INFO: 8, triagem.RUIDO: 5}
CHAVES = {triagem.ACAO: "acao", triagem.INFO: "info", triagem.RUIDO: "ruido"}


def emails_publicos(p: dict, agora: datetime) -> dict:
    """`p` = resultado de mail.painel.carregar. Suspeito (pelo triador ou pelo remetente) só conta; nunca aparece."""
    baldes, contagem = {}, {}
    suspeitos = len(p["grupos"][triagem.SUSPEITO])
    for nivel, chave in CHAVES.items():
        seguros = []
        for m in p["grupos"][nivel]:
            if _suspeito(m.remetente, m.assunto, m.previa):
                suspeitos += 1
            else:
                seguros.append(m)
        contagem[chave] = len(seguros)
        baldes[chave] = [_email(m) for m in seguros[:LIMITES[nivel]]]
    contagem["suspeito"] = suspeitos
    return {"gerado": agora.isoformat(), "sem_contas": bool(p.get("sem_contas")), "baldes": baldes, "contagem": contagem,
            "avisos": [AVISO_EMAIL] if p["avisos"] else []}


def briefing_publico(nome: str, agora: datetime, agenda: dict, emails: dict) -> dict:
    """O "bom dia" do celular: cumprimento + agenda de hoje + e-mails de ação. Sem clima, sem notícias, sem gravar nada."""
    parte = "Bom dia" if 5 <= agora.hour < 12 else "Boa tarde" if 12 <= agora.hour < 18 else "Boa noite"
    linhas = [f"{parte}, {limpo(nome, 40) or 'Maycon'}!"]
    if agenda["sem_agendas"]:
        linhas.append("Nenhuma agenda conectada no PC.")
    elif not agenda["hoje"]:
        linhas.append("Nenhum compromisso hoje.")
    else:
        linhas.append(f"Agenda de hoje ({len(agenda['hoje'])}):")
        for e in agenda["hoje"][:8]:
            quando = "dia inteiro" if e["dia_inteiro"] else datetime.fromisoformat(e["inicio"]).strftime("%H:%M")
            linhas.append(f"- {quando}: {e['titulo']}")
    if emails["sem_contas"]:
        linhas.append("Nenhuma conta de e-mail conectada no PC.")
    elif emails["baldes"]["acao"]:
        linhas.append(f"E-mails pedindo ação ({emails['contagem']['acao']}):")
        linhas += [f"- {e['de']}: {e['assunto']}" for e in emails["baldes"]["acao"][:5]]
    else:
        linhas.append("Nenhum e-mail importante pedindo ação agora.")
    if emails["contagem"]["suspeito"]:
        linhas.append(f"{emails['contagem']['suspeito']} e-mail(s) suspeito(s) separados; revise no PC.")
    return {"gerado": agora.isoformat(), "texto": "\n".join(linhas)}


def agentes_publicos(retrato: dict, subagentes: dict | None = None) -> dict:
    """Resumo do painel de agentes: só id, nome, estado e idade. Sem detalhe livre, caminho nem erro.
    `subagentes` (opcional) = {total, contagem, itens} já limpo por leitura_pc.sessoes_publicas."""
    def numero(v):
        return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    extra = {"subagentes": subagentes} if subagentes else {}
    return {**extra, "server_now": numero(retrato.get("server_now")), "resumo": {str(k): int(v) for k, v in (retrato.get("resumo") or {}).items()},
            "agentes": [{"id": limpo(a.get("id"), 30), "nome": limpo(a.get("nome"), 40), "state": limpo(a.get("state"), 10),
                         "age_s": numero(a.get("age_s"))} for a in retrato.get("agentes", [])]}


class _Cache:
    """Guarda o último resultado por `ttl` segundos. Falha não é guardada."""

    def __init__(self, funcao: Callable[[], dict], ttl: float, relogio: Callable[[], float]) -> None:
        self.funcao, self.ttl, self.relogio = funcao, ttl, relogio
        self._valor, self._ate, self._trava = None, 0.0, threading.Lock()

    def __call__(self) -> dict:
        with self._trava:
            agora = self.relogio()
            if self._valor is None or agora >= self._ate:
                self._valor, self._ate = self.funcao(), agora + self.ttl
            return self._valor


def montar(carregar_cfg: Callable[[], object], vivos: Callable[[], dict] = lambda: {}, relogio: Callable[[], float] = time.monotonic,
           agora: Callable[[], datetime] = datetime.now, ttl: float = TTL) -> dict[str, Callable[[], dict]]:
    """Callbacks do servidor do celular: {"agenda","emails","briefing","agentes","vitais","sessoes","tarefas","uso","radar"}. Só lê as fontes que o PC já tem conectadas."""
    def agenda() -> dict:
        from jarvis.agenda import servico

        cfg = carregar_cfg()
        semana = servico.da_semana(cfg, dias=7)
        prox = servico.proximo(cfg).get("proximo") if semana["ocorrencias"] or not semana.get("sem_agendas") else None
        return agenda_publica(semana, prox, agora().astimezone())

    def emails() -> dict:
        from jarvis.mail import painel

        cfg = carregar_cfg()
        if not (cfg.email.gmail_ativo or cfg.email.outlook_ativo or cfg.email.imap):
            p = {"grupos": {n: [] for n in (triagem.ACAO, triagem.INFO, triagem.RUIDO, triagem.SUSPEITO)}, "avisos": [], "sem_contas": True}
        else:
            p = painel.carregar(cfg, perguntar_ia=lambda _cfg, _mails: {})  # sem IA: só regras e heurística
        return emails_publicos(p, agora().astimezone())

    agenda_c, emails_c = _Cache(agenda, ttl, relogio), _Cache(emails, ttl, relogio)

    def briefing() -> dict:
        return briefing_publico(carregar_cfg().user_name, agora().astimezone(), agenda_c(), emails_c())

    from jarvis.mobile import leitura_montar, leitura_pc

    extra = leitura_montar.montar_extra(relogio=relogio, agora=agora)
    subagentes = extra.pop("_subagentes")

    def agentes() -> dict:
        from jarvis.agentes import painel

        sub = leitura_pc.sessoes_publicas([], subagentes(), 0.0, agora())["subagentes"]
        return agentes_publicos(painel.retrato(carregar_cfg(), vivos=vivos()), sub)

    return {"agenda": agenda_c, "emails": emails_c, "briefing": briefing, "agentes": agentes, **extra}

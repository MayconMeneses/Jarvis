"""Comandos locais (sem IA) de agenda, e-mail, notícias por assunto e "bom dia". Entram no motor local via PADROES/MODULOS."""

from __future__ import annotations

import re
from datetime import datetime

from jarvis.agenda import servico, texto

_NAO_ASSUNTO = r"(?!(tecnologia|tech|ti|hoje|gerais?|do dia|de hoje)$)"

# (intenção, regex sobre o texto já limpo: sem acento, minúsculo). Vão antes dos padrões genéricos do motor.
PADROES = [
    ("agenda_semana", r"^(minha agenda|agenda|compromissos|o que (eu )?tenho|o que (eu )?tem)\s+(da|desta|dessa|na|nesta|nessa|para a|pra)\s+semana$|^agenda da semana$"),
    ("agenda_hoje", r"^(minha agenda( de hoje)?|agenda( de hoje)?|meus compromissos( de hoje)?|compromissos de hoje|"
                    r"o que (eu )?tenho (para|pra|na agenda)? ?hoje|o que (eu )?tenho na agenda( hoje)?|o que tem na agenda( hoje)?)$"),
    ("agenda_proximo", r"^((qual (e )?)?(o )?(meu )?)?proximo (compromisso|evento|reuniao)$"),
    ("noticias_assunto", r"^noticias?\s+(sobre|de|do|da|dos|das)\s+" + _NAO_ASSUNTO + r"(?P<assunto>.{2,80})$"),
    ("email_importante", r"^(tem|ha|existe\w*)\s+(algum\s+)?e-?mail\s+(importante|urgente|de acao|que precise de acao)$|"
                         r"^e-?mails?\s+(importantes?|urgentes?|de acao)$|^tem algo importante no e-?mail$"),
    ("emails", r"^(meus e-?mails|ver (os |meus )?e-?mails|como (estao|esta) (os |meus |a minha )?(e-?mails|caixa de entrada)|"
               r"resumo (dos |de )?(meus )?e-?mails|e-?mails( novos| recentes| nao lidos)?)$"),
    ("bom_dia", r"^(bom dia|boa tarde|boa noite)( jarvis)?$"),
]
DIRETOS = {"agenda_hoje", "agenda_semana", "agenda_proximo", "noticias_assunto", "email_importante", "emails", "bom_dia"}


def hoje(_t, cfg) -> str:
    return texto.hoje(servico.do_dia(cfg))


def semana(_t, cfg) -> str:
    return texto.semana(servico.da_semana(cfg), datetime.now().astimezone())


def proximo(_t, cfg) -> str:
    return texto.proximo(servico.proximo(cfg))


def noticias(t, cfg) -> str:
    from jarvis.info import news
    from jarvis.local import engine

    assunto = re.sub(r"^noticias?\s+(sobre|de|do|da|dos|das)\s+", "", engine.clean(t)).strip()
    res = news.por_assunto(assunto, 5)
    if not res["manchetes"]:
        return f"Não achei notícias sobre “{assunto}” agora." + "".join(f" ({a})" for a in res["avisos"])
    return f"**Notícias sobre {assunto}:**\n" + "\n".join(f"- {h['titulo']} ({h['fonte']}) {h['link']}" for h in res["manchetes"])


def noticias_gerais(t, cfg) -> str:
    from jarvis.info import news
    from jarvis.local import engine

    kind = "tecnologia" if re.search(r"tecnolog|tech|ti\b", engine.clean(t)) else "gerais"
    items = news.headlines(kind, 5)["manchetes"]
    titulo = "de tecnologia" if kind == "tecnologia" else "de hoje"
    return f"**Notícias {titulo}:**\n" + "\n".join(f"- {h['titulo']} ({h['fonte']}) {h['link']}" for h in items)


def emails(_t, cfg) -> str:
    from jarvis.mail import painel

    return painel.texto(painel.carregar(cfg))


def importante(_t, cfg) -> str:
    from jarvis.mail import painel

    return painel.texto(painel.carregar(cfg), so_acao=True)


def bom_dia(_t, cfg) -> str:
    from jarvis import briefing

    return briefing.build(cfg, forcar=True)["text"]


MODULOS = {"agenda_hoje": hoje, "agenda_semana": semana, "agenda_proximo": proximo, "noticias_assunto": noticias, "noticias": noticias_gerais,
           "emails": emails, "email_importante": importante, "bom_dia": bom_dia}

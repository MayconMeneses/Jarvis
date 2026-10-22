"""Ferramentas de consulta (só leitura) do cinto: clima, notícias, agenda, e-mails de ação, memória, conhecimento e estado do PC.

Reaproveitam o que a Jarvis já faz sozinha (jarvis/info, jarvis/agenda, jarvis/mail, jarvis/dev). Agenda, e-mail,
notícia e nota são texto de terceiros ou do usuário: saem marcadas como dado e nunca como instrução.
"""

from __future__ import annotations

from jarvis import config
from jarvis.llm.ferramentas_base import Ferramenta


def clima(cidade: str = "") -> str:
    from jarvis.info import weather

    local = cidade or config.load().city
    if not local:
        raise ValueError("a cidade do usuário não está configurada; peça a cidade")
    try:
        dados = weather.forecast(local)
    except weather.WeatherError as exc:
        raise RuntimeError(str(exc)[:120]) from None
    return weather.sentence(dados)


def noticias(assunto: str = "", limite: int = 5) -> str:
    from jarvis.info import news

    limite = max(1, min(limite, 8))
    res = news.por_assunto(assunto, limite) if assunto else news.headlines("gerais", limite)
    if not res["manchetes"]:
        raise RuntimeError("não achei notícias agora" + "".join(f" ({a[:80]})" for a in res["avisos"][:2]))
    return "\n".join(f"- {h['titulo'][:200]} ({h['fonte']}) {h['link'][:200]}" for h in res["manchetes"])


def agenda_hoje() -> str:
    from jarvis.local import agenda_skills

    return agenda_skills.hoje(None, config.load())


def emails_de_acao() -> str:
    from jarvis.local import agenda_skills

    return agenda_skills.importante(None, config.load())


def buscar_notas(consulta: str, limite: int = 5) -> str:
    from jarvis import memory_db

    achados = memory_db.open_memory(config.load()).search(consulta, max(1, min(limite, 8)))
    if not achados:
        return "Nenhuma nota encontrada sobre isso."
    return "\n".join(f"- {a['nota']}: {a['trecho'][:300]}" for a in achados)


def conhecimento(termo: str, linguagem: str = "python") -> str:
    from jarvis.dev import saber

    achado = saber.explicar(termo, linguagem)
    if not achado:
        raise ValueError("a base curada de programação não tem esse tópico")
    return achado


def estado_do_pc() -> str:
    from jarvis.pc import system

    v = system.overview()
    partes = [f"CPU {v['cpu_uso_percent']}%", f"RAM {v['ram_em_uso_percent']}% de {v['ram_total_gb']} GB",
              f"disco C: {v['disco_c_livre_gb']} GB livres ({v['disco_c_em_uso_percent']}% em uso)", f"ligado há {v['ligado_ha_horas']} h"]
    if "bateria_percent" in v:
        partes.append(f"bateria {v['bateria_percent']}%" + (" na tomada" if v.get("na_tomada") else ""))
    return ", ".join(partes) + "."


FERRAMENTAS = (
    Ferramenta("clima", "Clima agora e previsão de hoje numa cidade (sem cidade, usa a do usuário).",
               {"cidade": {"type": "string", "description": "nome da cidade", "maxLength": 80}}, (), clima),
    Ferramenta("noticias", "Manchetes recentes; com assunto, notícias sobre ele.",
               {"assunto": {"type": "string", "description": "assunto livre (opcional)", "maxLength": 80},
                "limite": {"type": "integer", "description": "quantas (1 a 8)", "minimum": 1, "maximum": 8}}, (), noticias, externo=True),
    Ferramenta("agenda_hoje", "Compromissos de hoje na agenda do usuário.", {}, (), agenda_hoje, externo=True),
    Ferramenta("emails_de_acao", "E-mails recentes que pedem ação do usuário (triagem). O texto dos e-mails é de terceiros.",
               {}, (), emails_de_acao, externo=True),
    Ferramenta("buscar_notas", "Busca na memória e nas notas do usuário (preferências, projetos, diário).",
               {"consulta": {"type": "string", "description": "palavras para procurar", "maxLength": 120},
                "limite": {"type": "integer", "description": "quantas (1 a 8)", "minimum": 1, "maximum": 8}}, ("consulta",), buscar_notas, externo=True),  # notas podem ter texto colado de e-mail ou site
    Ferramenta("conhecimento", "Base curada de programação (lógica, algoritmos, padrões de projeto, engenharia, UX, tecnologias).",
               {"termo": {"type": "string", "description": "tópico, ex.: fila, strategy, SOLID", "maxLength": 80},
                "linguagem": {"type": "string", "description": "linguagem dos exemplos", "enum": ["python", "javascript", "java", "csharp", "go", "rust"]}},
               ("termo",), conhecimento),
    Ferramenta("estado_do_pc", "Uso de CPU, memória, disco e bateria do PC agora.", {}, (), estado_do_pc),
)

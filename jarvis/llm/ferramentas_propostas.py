"""Ferramentas de PROPOSTA do cinto: o modelo só cria um cartão pendente; quem executa é o usuário, no Aprovar.

- propor_memoria: "Guardar esta lembrança?" (reaproveita jarvis/llm/memoria_viva.py);
- propor_lembrete: aviso falado/escrito numa data e hora (cartão "criar_lembrete");
- propor_abrir_app: abrir um programa do Menu Iniciar (cartão "abrir_app").
`executar_cartao` roda só depois do Aprovar (jarvis/pc/actions.execute) e valida tudo DE NOVO.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.config import data_dir
from jarvis.llm.ferramentas_base import Ferramenta

KINDS = ("criar_lembrete", "abrir_app")
MAX_LEMBRETES = 50
MAX_TEXTO_LEMBRETE = 140
_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")
_QUANDO = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}$")
AVISO_TERCEIROS = "\nAtenção: neste turno a IA leu conteúdo de terceiros (site, e-mail ou notícia). Só aprove se o pedido for mesmo seu."


def arquivo_lembretes() -> Path:
    return data_dir() / "lembretes.json"


def ler_lembretes(arquivo: Path | None = None) -> list[dict]:
    try:
        dados = json.loads((arquivo or arquivo_lembretes()).read_text(encoding="utf-8"))
        return [d for d in dados if isinstance(d, dict)] if isinstance(dados, list) else []
    except (OSError, ValueError):
        return []


def gravar_lembretes(lista: list[dict], arquivo: Path | None = None) -> None:
    alvo = arquivo or arquivo_lembretes()
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps(lista[-200:], ensure_ascii=False), encoding="utf-8")


def validar_lembrete(texto: str, quando: str, agora: datetime | None = None) -> tuple[str, datetime]:
    """(texto limpo, momento). Levanta ValueError se o texto ou a data não servem; o momento precisa estar no futuro (até 1 ano)."""
    agora = agora or datetime.now()
    texto = " ".join(str(texto).split())
    if not texto or len(texto) > MAX_TEXTO_LEMBRETE or _CONTROLE.search(texto) or "[[" in texto:
        raise ValueError(f"o texto do lembrete precisa ter de 1 a {MAX_TEXTO_LEMBRETE} caracteres")
    if not _QUANDO.match(str(quando).strip()):
        raise ValueError("use a data e hora no formato AAAA-MM-DD HH:MM")
    try:
        momento = datetime.fromisoformat(quando.strip().replace(" ", "T"))
    except ValueError:
        raise ValueError("data ou hora inexistente") from None
    if momento < agora - timedelta(minutes=1) or momento > agora + timedelta(days=366):
        raise ValueError("o lembrete precisa ser no futuro e dentro de um ano")
    return texto, momento


def _salvar_acao(tipo: str, params: dict, descricao: str, terceiros: bool, motivo: str):
    from jarvis.pc import actions

    return actions.ActionStore().save(actions.Action(tipo, params, descricao + (AVISO_TERCEIROS if terceiros else ""),
                                                     f"sugestão do cérebro generativo ({motivo[:80]}); nada acontece se você recusar"))


def propor_memoria(area: str, titulo: str, fato: str, terceiros=lambda: False) -> str:
    from jarvis import config, memory_db
    from jarvis.llm import memoria_viva
    from jarvis.pc import actions

    item = memoria_viva.validar(area, titulo, " ".join(fato.split()))
    memoria_viva.propor(actions.ActionStore(), memory_db.open_memory(config.load()), item, "cérebro generativo",
                        ["conteúdo lido neste turno"] if terceiros() else None)
    return "Proposta criada: aparece um cartão na janela para o usuário aprovar. Diga que deixou a proposta; NÃO diga que foi salvo."


def propor_lembrete(texto: str, quando: str, terceiros=lambda: False) -> str:
    texto, momento = validar_lembrete(texto, quando)
    if len(ler_lembretes()) >= MAX_LEMBRETES:
        raise ValueError("já existem lembretes demais pendentes")
    _salvar_acao("criar_lembrete", {"texto": texto, "quando": momento.isoformat(timespec="minutes")},
                 f"Criar um lembrete para {momento:%d/%m/%Y às %H:%M}: “{texto}”. A Jarvis avisa na janela (e fala, fora do horário de silêncio).",
                 terceiros(), "lembrete")
    return "Proposta criada: o usuário precisa aprovar o cartão do lembrete na janela. NÃO diga que já foi criado."


def propor_abrir_app(nome: str, terceiros=lambda: False) -> str:
    from jarvis.pc import launcher

    achado = launcher.find_app(nome, launcher.app_index())
    if not achado:
        raise ValueError(f"não encontrei o programa '{nome[:40]}' no Menu Iniciar")
    _salvar_acao("abrir_app", {"nome": achado[0]}, f"Abrir o programa “{achado[0]}” (Menu Iniciar).", terceiros(), "abrir programa")
    return "Proposta criada: o usuário precisa aprovar o cartão para abrir o programa. NÃO diga que já foi aberto."


def executar_cartao(action) -> str:
    """Só depois do Aprovar. Revalida os parâmetros (o arquivo da ação pode ter sido alterado)."""
    p = action.params
    if action.kind == "criar_lembrete":
        texto, momento = validar_lembrete(p.get("texto", ""), p.get("quando", ""))
        lista = ler_lembretes()
        if len([x for x in lista if not x.get("avisado")]) >= MAX_LEMBRETES:
            raise ValueError("já existem lembretes demais pendentes")
        lista.append({"id": uuid.uuid4().hex[:10], "texto": texto, "quando": momento.isoformat(timespec="minutes"), "avisado": False})
        gravar_lembretes(lista)
        return f"Lembrete criado para {momento:%d/%m/%Y às %H:%M}."
    if action.kind == "abrir_app":
        from jarvis.pc import launcher

        return launcher.open_app(str(p.get("nome", ""))[:80])
    raise ValueError(f"cartão desconhecido: {action.kind}")


def _com(funcao, terceiros):
    return lambda **kw: funcao(**kw, terceiros=terceiros)


def ferramentas(terceiros=lambda: False) -> tuple[Ferramenta, ...]:
    """As propostas; `terceiros()` diz se o turno leu conteúdo de terceiros (o cartão então avisa)."""
    return (
        Ferramenta("propor_memoria", "PROPÕE guardar uma lembrança durável sobre o usuário (ele aprova num cartão). Nunca senhas nem dados de e-mail/site.",
                   {"area": {"type": "string", "description": "metas, trabalho, projetos, financas, aprendizado, saude, relacoes ou meta", "maxLength": 20},
                    "titulo": {"type": "string", "description": "título curto (até 60 caracteres)", "maxLength": 60},
                    "fato": {"type": "string", "description": "o que lembrar (até 600 caracteres)", "maxLength": 600}},
                   ("area", "titulo", "fato"), _com(propor_memoria, terceiros), "proposta"),
        Ferramenta("propor_lembrete", "PROPÕE criar um lembrete numa data e hora futuras (o usuário aprova num cartão).",
                   {"texto": {"type": "string", "description": "o que lembrar", "maxLength": MAX_TEXTO_LEMBRETE},
                    "quando": {"type": "string", "description": "data e hora locais: AAAA-MM-DD HH:MM", "maxLength": 16}},
                   ("texto", "quando"), _com(propor_lembrete, terceiros), "proposta"),
        Ferramenta("propor_abrir_app", "PROPÕE abrir um programa do Menu Iniciar (o usuário aprova num cartão).",
                   {"nome": {"type": "string", "description": "nome do programa", "maxLength": 60}},
                   ("nome",), _com(propor_abrir_app, terceiros), "proposta"),
    )

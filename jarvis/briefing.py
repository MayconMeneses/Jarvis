"""Saudação ao abrir a Jarvis.

Sempre: cumprimento, "como você está?" e o clima. Na primeira abertura do dia,
também as manchetes gerais e de tecnologia, salvas em Relatórios na memória da Jarvis.
Montado sem IA: rápido e sem gastar o limite da assinatura.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

from jarvis import memory_db
from jarvis.config import Config, data_dir
from jarvis.info import jobs, news, weather

log = logging.getLogger(__name__)


def salutation(name: str, now: datetime) -> str:
    part = "Bom dia" if 5 <= now.hour < 12 else "Boa tarde" if 12 <= now.hour < 18 else "Boa noite"
    return f"{part}, {name}!"


def _state_path() -> Path:
    return data_dir() / "estado.json"


def is_first_today(state_path: Path, today: date) -> bool:
    try:
        return json.loads(state_path.read_text(encoding="utf-8")).get("ultimo_briefing") != today.isoformat()
    except (OSError, ValueError):
        return True


def mark_done(state_path: Path, today: date) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"ultimo_briefing": today.isoformat()}), encoding="utf-8")


def new_jobs(cfg: Config) -> tuple[str, str]:
    """Até 3 vagas novas compatíveis. ("", "") se não houver perfil ou vagas."""
    try:
        profile, _ = jobs.load_profile(memory_db.open_memory(cfg))
        if jobs.profile_is_empty(profile):
            text = "Preencha o seu perfil profissional para eu buscar vagas (ou me diga sua stack e nível)."
            return f"\n**Vagas:** {text}", text
        found = jobs.find(profile, limit=3, only_new=True)["vagas"]
    except Exception:
        log.warning("falha ao buscar vagas", exc_info=True)
        return "", ""
    if not found:
        return "", ""
    items = "\n".join(f"• {j['titulo']} — {j['local']} (nota {j['nota']}, {j['fonte']})\n  {j['link']}" for j in found)
    return f"\n**Vagas novas para você:**\n{items}", f"Encontrei {len(found)} vagas novas compatíveis com você."


def build(
    cfg: Config,
    now: datetime | None = None,
    state_path: Path | None = None,
    get_weather=weather.forecast,
    get_news=news.headlines,
    get_jobs=new_jobs,
) -> dict:
    now = now or datetime.now()
    state_path = state_path or _state_path()
    full = is_first_today(state_path, now.date())

    hello = f"{salutation(cfg.user_name, now)} Como você está?"
    lines, spoken = [hello], [hello]

    if cfg.city:
        try:
            sentence = weather.sentence(get_weather(cfg.city))
            lines.append(sentence)
            spoken.append(sentence)
        except weather.WeatherError as exc:
            lines.append(f"(Clima indisponível agora: {exc})")
    else:
        ask = "Me diga sua cidade para eu trazer o clima, por exemplo: “minha cidade é Fortaleza”."
        lines.append(ask)
        spoken.append(ask)

    headlines: dict[str, list[dict]] = {}
    if full:
        for kind, label in (("gerais", "Destaques de hoje"), ("tecnologia", "Tecnologia")):
            found = get_news(kind, 3)["manchetes"]
            headlines[kind] = found
            if found:
                lines.append(f"\n**{label}:**\n" + "\n".join(f"• {h['titulo']} ({h['fonte']})" for h in found))
        tops = [h[0]["titulo"] for h in headlines.values() if h]
        if tops:
            spoken.append("Destaques: " + ". ".join(tops) + ".")
        job_lines, job_spoken = get_jobs(cfg)
        if job_lines:
            lines.append(job_lines)
            spoken.append(job_spoken)
        spoken.append("Os detalhes estão na janela.")
        mark_done(state_path, now.date())
        _save_report(cfg, "\n".join(lines))

    return {"text": "\n".join(lines), "speak": " ".join(spoken), "completo": full, "manchetes": headlines}


def _save_report(cfg: Config, text: str) -> None:
    try:
        mem = memory_db.open_memory(cfg)
        mem.save_report("Briefing", f"# Briefing {date.today():%d/%m/%Y}\n\n{text}\n")
        mem.diary("Briefing do dia apresentado.")
    except (sqlite3.Error, OSError, ValueError):
        log.warning("não foi possível salvar o briefing na memória", exc_info=True)

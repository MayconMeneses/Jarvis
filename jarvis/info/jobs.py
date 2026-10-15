"""Vagas de desenvolvimento de fontes públicas e gratuitas.

- Repositórios de vagas da comunidade no GitHub (cada vaga é uma issue aberta).
- Remotive (vagas remotas). Termos: no máximo ~4 consultas por dia, link para a vaga
  original e citar a Remotive como fonte. Por isso o cache de 6 horas.

A Jarvis nunca se candidata: só mostra a vaga e o link.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from jarvis.config import data_dir

GITHUB_REPOS = ("frontendbr/vagas", "backend-br/vagas", "react-brasil/vagas")
REMOTIVE = "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"
CACHE_SECONDS = 6 * 3600
MIN_SCORE = 30


@dataclass
class Job:
    id: str
    titulo: str
    local: str
    fonte: str
    link: str
    publicada: str  # ISO 8601
    etiquetas: list[str] = field(default_factory=list)
    descricao: str = ""


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _get_json(url: str, opener=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={
        "User-Agent": "SuperJarvis/0.1 (assistente pessoal)", "Accept": "application/json",
    })
    with opener(request, timeout=20) as resp:
        return json.loads(resp.read(5_000_000).decode("utf-8"))


def _plain(text: str | None, limit: int = 500) -> str:
    text = re.sub(r"<[^>]+>|[#*_`>|]", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def from_github(repo: str, opener=urllib.request.urlopen) -> list[Job]:
    issues = _get_json(f"https://api.github.com/repos/{repo}/issues?state=open&per_page=50&sort=created", opener)
    jobs = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        title = issue.get("title", "")
        match = re.match(r"\s*\[([^\]]+)\]\s*(.*)", title)
        jobs.append(Job(
            id=f"gh:{repo}#{issue['number']}",
            titulo=(match.group(2) if match else title).strip(),
            local=match.group(1).strip() if match else "",
            fonte=f"GitHub {repo}",
            link=issue.get("html_url", ""),
            publicada=issue.get("created_at", ""),
            etiquetas=[label["name"] for label in issue.get("labels", [])],
            descricao=_plain(issue.get("body")),
        ))
    return jobs


def from_remotive(opener=urllib.request.urlopen) -> list[Job]:
    data = _get_json(REMOTIVE, opener)
    return [
        Job(
            id=f"remotive:{job['id']}",
            titulo=job.get("title", ""),
            local=f"Remoto ({job.get('candidate_required_location') or 'qualquer lugar'})",
            fonte="Remotive",
            link=job.get("url", ""),
            publicada=job.get("publication_date", ""),
            etiquetas=list(job.get("tags") or []) + [job.get("company_name", "")],
            descricao=_plain(job.get("description")),
        )
        for job in data.get("jobs", [])
    ]


def collect(cache: Path | None = None, now: float | None = None, opener=urllib.request.urlopen) -> dict:
    """Todas as vagas, do cache se tiver menos de 6 horas."""
    cache = cache or data_dir() / "vagas_cache.json"
    now = now or time.time()
    try:
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if now - saved["quando"] < CACHE_SECONDS:
            return {"vagas": [Job(**j) for j in saved["vagas"]], "avisos": saved.get("avisos", [])}
    except (OSError, ValueError, KeyError, TypeError):
        pass

    jobs, warnings = [], []
    sources = [(repo, lambda r=repo: from_github(r, opener)) for repo in GITHUB_REPOS]
    sources.append(("Remotive", lambda: from_remotive(opener)))
    for name, load in sources:
        try:
            jobs += load()
        except Exception as exc:  # uma fonte fora do ar não derruba as outras
            warnings.append(f"{name}: {exc}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"quando": now, "vagas": [asdict(j) for j in jobs], "avisos": warnings},
                                ensure_ascii=False), encoding="utf-8")
    return {"vagas": jobs, "avisos": warnings}


# ── perfil e pontuação ───────────────────────────────────────────────────

PROFILE_TEMPLATE = """---
tipo: perfil
---
# Perfil Profissional

A Jarvis usa este perfil para escolher vagas. Preencha depois dos dois-pontos
(você também pode pedir por voz: "Jarvis, meu nível é pleno").

Exemplos — Stack: Python, React, Node · Nível: júnior, pleno ou sênior ·
Modalidade: remoto, híbrido ou presencial · Evitar: PHP · Inglês: básico, intermediário ou fluente

Stack:
Nível:
Modalidade:
Cidade:
Evitar:
Inglês:
"""
PROFILE_FIELDS = ("Stack", "Nível", "Modalidade", "Cidade", "Evitar", "Inglês")
PROFILE_REF = "Perfil Profissional"


def load_profile(mem) -> tuple[dict, str]:
    """Lê o perfil na memória da Jarvis, criando o modelo vazio se não existir."""
    text = mem.get(PROFILE_REF)
    if text is None:
        text = PROFILE_TEMPLATE.split("---\n", 2)[-1]  # sem o cabeçalho de nota do Obsidian
        mem.put(PROFILE_REF, text, "perfil")
    return parse_profile(text), PROFILE_REF


def update_profile(mem, field_name: str, value: str) -> str:
    match = next((f for f in PROFILE_FIELDS if _fold(f) == _fold(field_name.strip())), None)
    if match is None:
        raise ValueError(f"campo inválido; use um de: {', '.join(PROFILE_FIELDS)}")
    load_profile(mem)
    value = value.replace("\n", " ").strip()[:200]
    lines = (mem.get(PROFILE_REF) or "").splitlines()
    for i, line in enumerate(lines):
        if _fold(line.split(":", 1)[0].strip()) == _fold(match) and ":" in line:
            lines[i] = f"{match}: {value}"
            break
    else:
        lines.append(f"{match}: {value}")
    return mem.put(PROFILE_REF, "\n".join(lines) + "\n", "perfil")


def profile_is_empty(profile: dict) -> bool:
    return not profile["stack"] and not profile["nivel"] and not profile["modalidade"]

LEVELS = {"junior": ("junior", "jr", "estagio", "estagiario", "trainee"),
          "pleno": ("pleno", "pl", "mid", "intermediate"),
          "senior": ("senior", "sr", "lead", "staff", "principal", "especialista", "tech lead")}
REMOTE_WORDS = ("remoto", "remote", "anywhere", "worldwide", "home office", "100% remoto")


def parse_profile(text: str) -> dict:
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.strip().startswith(("-", "#")):
            fields[_fold(key.strip())] = value.strip()
    split = lambda v: [p.strip() for p in re.split(r"[,;/]", v or "") if p.strip()]  # noqa: E731
    return {
        "stack": split(fields.get("stack")),
        "nivel": _fold(fields.get("nivel", "")),
        "modalidade": _fold(fields.get("modalidade", "")),
        "cidade": fields.get("cidade", ""),
        "evitar": split(fields.get("evitar")),
        "ingles": _fold(fields.get("ingles", "")),
    }


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(_fold(word))}(?![a-z0-9])", text) is not None


def score(job: Job, profile: dict, now: datetime | None = None) -> tuple[int, list[str]]:
    text = _fold(" ".join([job.titulo, job.local, " ".join(job.etiquetas), job.descricao]))
    head = _fold(" ".join([job.titulo, " ".join(job.etiquetas)]))
    points, reasons = 0, []

    hits = [s for s in profile["stack"] if _has_word(text, s)]
    if hits:
        points += min(45, 15 * len(hits))
        reasons.append("usa " + ", ".join(hits))

    level = profile["nivel"]
    job_levels = {name for name, words in LEVELS.items() if any(_has_word(head, w) for w in words)}
    if level and job_levels:
        if level in job_levels:
            points += 20
            reasons.append(f"nível {level}")
        elif level == "junior" and "senior" in job_levels:
            points -= 25
            reasons.append("pede nível sênior")

    remote = any(_has_word(text, w) for w in REMOTE_WORDS)
    if "remoto" in profile["modalidade"]:
        if remote:
            points += 20
            reasons.append("remota")
        elif profile["cidade"] and _fold(profile["cidade"]) in _fold(job.local):
            points += 10
            reasons.append(f"em {profile['cidade']}")
        else:
            points -= 20
            reasons.append("presencial/híbrida fora da sua cidade")
    elif profile["cidade"] and _fold(profile["cidade"]) in _fold(job.local):
        points += 20
        reasons.append(f"em {profile['cidade']}")

    avoided = [w for w in profile["evitar"] if _has_word(text, w)]
    if avoided:
        points -= 40
        reasons.append("envolve " + ", ".join(avoided) + " (que você quer evitar)")

    if job.fonte == "Remotive" and profile["ingles"] in ("", "basico", "nenhum"):
        points -= 10
        reasons.append("vaga em inglês")

    try:
        published = datetime.fromisoformat(job.publicada.replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if ((now or datetime.now(timezone.utc)) - published).days <= 3:
            points += 10
            reasons.append("publicada nos últimos 3 dias")
    except ValueError:
        pass
    return max(0, min(100, points)), reasons


# ── vagas já mostradas ───────────────────────────────────────────────────

class SeenStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "vagas_vistas.json"

    def load(self) -> dict[str, str]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def add(self, ids: list[str]) -> None:
        seen = self.load()
        today = datetime.now().date().isoformat()
        seen.update({i: seen.get(i, today) for i in ids})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(seen), encoding="utf-8")


def find(profile: dict, limit: int = 8, only_new: bool = False,
         collected: dict | None = None, seen: SeenStore | None = None) -> dict:
    collected = collected or collect()
    seen = seen or SeenStore()
    already = seen.load()
    ranked = []
    for job in collected["vagas"]:
        points, reasons = score(job, profile)
        is_new = job.id not in already
        if points >= MIN_SCORE and (is_new or not only_new):
            ranked.append({**asdict(job), "nota": points, "motivos": reasons, "nova": is_new})
    ranked.sort(key=lambda j: (j["nota"], j["publicada"]), reverse=True)
    chosen = ranked[:max(1, min(limit, 20))]
    for job in chosen:
        job["descricao"] = job["descricao"][:300]
    seen.add([j["id"] for j in chosen])
    return {"vagas": chosen, "total_compativeis": len(ranked), "avisos": collected["avisos"]}

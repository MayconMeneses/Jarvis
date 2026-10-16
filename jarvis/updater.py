"""Atualização automática: procura versão nova nas Releases do GitHub, baixa e confere o instalador.

Só roda na Jarvis instalada. O instalador vem do repositório da própria Jarvis, por HTTPS, e só é
usado se o SHA-256 baixado for igual ao publicado pelo GitHub para aquele arquivo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import urllib.request
from pathlib import Path

from jarvis import __version__

log = logging.getLogger(__name__)

REPO = "MayconMeneses/Jarvis"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
ASSET = re.compile(r"^SuperJarvis-Setup-(\d+\.\d+\.\d+)\.exe$")
PENDING = "pendente.json"
TIMEOUT = 20


def parse_version(text: str) -> tuple[int, ...]:
    """'v0.16.1' -> (0, 16, 1). Texto fora do padrão vira () e nunca é 'mais novo'."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text.strip())
    return tuple(int(n) for n in match.groups()) if match else ()


def is_newer(candidate: str, current: str = __version__) -> bool:
    return bool(parse_version(candidate)) and parse_version(candidate) > parse_version(current)


def _get(url: str, opener=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={"User-Agent": "SuperJarvis", "Accept": "application/vnd.github+json"})
    return opener(request, timeout=TIMEOUT)


def latest_release(opener=urllib.request.urlopen) -> dict | None:
    """A versão mais nova publicada: {version, name, url, sha256, notes}, ou None se não há instalador válido."""
    with _get(API, opener) as resp:
        release = json.loads(resp.read().decode("utf-8"))
    for asset in release.get("assets", []):
        match = ASSET.match(asset.get("name", ""))
        digest = str(asset.get("digest") or "")
        url = asset.get("browser_download_url", "")
        if match and digest.startswith("sha256:") and url.startswith(DOWNLOAD_PREFIX):
            return {"version": match.group(1), "name": asset["name"], "url": url,
                    "sha256": digest.removeprefix("sha256:").lower(), "notes": (release.get("body") or "")[:600]}
    return None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(info: dict, folder: Path, opener=urllib.request.urlopen) -> Path:
    """Baixa para uma pasta da Jarvis, confere o SHA-256 e registra como pendente de instalação."""
    if not info["url"].startswith(DOWNLOAD_PREFIX):
        raise ValueError("endereço de download fora do repositório da Jarvis")
    folder.mkdir(parents=True, exist_ok=True)
    final, part = folder / info["name"], folder / (info["name"] + ".part")
    with _get(info["url"], opener) as resp, part.open("wb") as out:
        for block in iter(lambda: resp.read(1 << 20), b""):
            out.write(block)
    if sha256_of(part) != info["sha256"]:
        part.unlink(missing_ok=True)
        raise ValueError("o instalador baixado não confere com o SHA-256 publicado")
    part.replace(final)
    (folder / PENDING).write_text(json.dumps({"version": info["version"], "file": final.name,
                                              "sha256": info["sha256"]}), encoding="utf-8")
    return final


def pending(folder: Path, current: str = __version__) -> dict | None:
    """Instalador já baixado e ainda válido (mais novo que o instalado e com SHA-256 igual)."""
    try:
        meta = json.loads((folder / PENDING).read_text(encoding="utf-8"))
        path = folder / meta["file"]
        if is_newer(meta["version"], current) and path.is_file() and sha256_of(path) == meta["sha256"]:
            return {"version": meta["version"], "path": path}
    except (OSError, ValueError, KeyError):
        pass
    return None


def cleanup(folder: Path, current: str = __version__) -> None:
    """Remove instaladores que já foram instalados (versão igual ou menor que a atual)."""
    if pending(folder, current) is not None or not folder.is_dir():
        return
    for item in folder.iterdir():
        if item.name == PENDING or ASSET.match(item.name) or item.name.endswith(".part"):
            item.unlink(missing_ok=True)


def check(folder: Path, current: str = __version__, opener=urllib.request.urlopen) -> dict:
    """Procura e baixa a atualização. Devolve {'estado': 'atual'|'pronta'|'erro', 'versao', 'mensagem'}."""
    try:
        ready = pending(folder, current)
        if ready:
            return {"estado": "pronta", "versao": ready["version"]}
        cleanup(folder, current)
        info = latest_release(opener)
        if info is None or not is_newer(info["version"], current):
            return {"estado": "atual", "versao": current}
        download(info, folder, opener)
        return {"estado": "pronta", "versao": info["version"], "notas": info["notes"]}
    except Exception as exc:  # sem internet, limite da API, arquivo corrompido: nunca derruba a Jarvis
        log.warning("atualização automática falhou: %s", exc)
        return {"estado": "erro", "mensagem": str(exc)}


def install(folder: Path, current: str = __version__, runner=None) -> bool:
    """Roda o instalador baixado em modo silencioso; ele fecha esta Jarvis e abre a nova."""
    ready = pending(folder, current)  # confere o SHA-256 de novo, logo antes de executar
    if ready is None:
        return False
    (runner or subprocess.Popen)([str(ready["path"]), "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/NORESTART"],
           creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    return True

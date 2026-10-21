"""Abrir programas, sites, pastas e projetos.

Só abre o que é seguro abrir sem aprovação:
- programas: apenas os do Menu Iniciar (Get-StartApps) ou atalhos fixos do Windows;
- sites: apenas http(s);
- pastas: apenas pastas que existem (abre no Explorador);
- projetos: os cadastrados, no VS Code.
Nunca executa um caminho de arquivo arbitrário.
"""

from __future__ import annotations

import difflib
import json
import os
import shutil
import time
import unicodedata
import webbrowser
from pathlib import Path

from jarvis import proc as processos
from jarvis.config import data_dir

CACHE_SECONDS = 24 * 3600

# Programas do Windows por apelido (pt-BR e en).
BUILTIN = {
    "calculadora": "calc.exe", "calculator": "calc.exe",
    "bloco de notas": "notepad.exe", "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe", "prompt de comando": "cmd.exe",
    "powershell": "powershell.exe",
    "gerenciador de tarefas": "taskmgr.exe", "task manager": "taskmgr.exe",
    "explorador de arquivos": "explorer.exe", "explorer": "explorer.exe",
    "painel de controle": "control.exe",
    "configuracoes": "ms-settings:", "configurações": "ms-settings:",
}
BROWSER_WORDS = {"navegador", "browser", "internet"}
# Apelidos falados → nome como aparece no Menu Iniciar.
NICKNAMES = {
    "vs code": "visual studio code", "vscode": "visual studio code", "code": "visual studio code",
    "zap": "whatsapp", "whats": "whatsapp", "chrome": "google chrome", "edge": "microsoft edge",
    "terminal do windows": "terminal", "docker": "docker desktop",
}


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().strip())
                   if unicodedata.category(c) != "Mn")


# ── índice de programas ──────────────────────────────────────────────────

def _load_start_apps() -> dict[str, str]:
    script = "Get-StartApps | ForEach-Object { $_.Name + \"`t\" + $_.AppID }"
    result = processos.executar(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    apps = {}
    for line in result.stdout.splitlines():
        name, sep, app_id = line.partition("\t")
        if sep and name.strip() and app_id.strip():
            apps[name.strip()] = app_id.strip()
    return apps


def app_index(cache: Path | None = None, loader=_load_start_apps, now: float | None = None) -> dict[str, str]:
    cache = cache or data_dir() / "apps.json"
    now = now or time.time()
    try:
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if now - saved["quando"] < CACHE_SECONDS and saved["apps"]:
            return saved["apps"]
    except (OSError, ValueError, KeyError):
        pass
    apps = loader()
    if apps:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"quando": now, "apps": apps}, ensure_ascii=True), encoding="utf-8")
    return apps


def find_app(query: str, apps: dict[str, str]) -> tuple[str, str] | None:
    """(nome, AppID) mais parecido com o pedido, ou None."""
    q = fold(query)
    q = NICKNAMES.get(q, q)
    folded = {fold(name): name for name in apps}
    if q in folded:
        name = folded[q]
        return name, apps[name]
    contains = [f for f in folded if q in f or (len(f) > 3 and f in q)]
    if contains:
        name = folded[min(contains, key=len)]
        return name, apps[name]
    close = difflib.get_close_matches(q, list(folded), n=1, cutoff=0.75)
    if close:
        name = folded[close[0]]
        return name, apps[name]
    return None


# ── abrir ────────────────────────────────────────────────────────────────

def open_app(query: str, apps: dict[str, str] | None = None, runner=processos.abrir_visivel) -> str:
    q = fold(query)
    if q in BROWSER_WORDS:
        webbrowser.open("https://www.google.com")
        return "Navegador aberto."
    builtin = next((exe for alias, exe in BUILTIN.items() if fold(alias) == q), None)
    if builtin:
        if builtin.endswith(":"):
            os.startfile(builtin)  # ms-settings:
        else:
            # cmd e PowerShell são programas de console: aqui o console novo é justamente o que o usuário pediu.
            console = processos.CREATE_NEW_CONSOLE if builtin in ("cmd.exe", "powershell.exe") else 0
            runner([builtin], creationflags=console)
        return f"{query.strip().capitalize()} aberto."
    found = find_app(query, apps if apps is not None else app_index())
    if not found:
        raise ValueError(f"não encontrei o programa '{query}' no Menu Iniciar")
    name, app_id = found
    runner(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
    return f"{name} aberto."


def open_site(target: str) -> str:
    url = target.strip()
    if not url.lower().startswith(("http://", "https://")):
        if " " in url or "." not in url:
            raise ValueError("informe um endereço de site (ex.: github.com) ou use a pesquisa")
        url = "https://" + url  # sempre http(s): nada de file:, javascript: etc.
    webbrowser.open(url)
    return f"Abrindo {url} no navegador."


def special_folders() -> dict[str, Path]:
    home = Path.home()
    onedrive_desktop = home / "OneDrive" / "Área de Trabalho"
    return {
        "documentos": home / "Documents", "downloads": home / "Downloads",
        "area de trabalho": onedrive_desktop if onedrive_desktop.is_dir() else home / "Desktop",
        "imagens": home / "Pictures", "musicas": home / "Music", "videos": home / "Videos",
        "jarvis": home / "Documents" / "Jarvis",
    }


def open_folder(target: str, runner=processos.abrir_visivel) -> str:
    folder = special_folders().get(fold(target))
    if folder is None:
        candidate = Path(target.strip().strip('"')).expanduser()
        folder = candidate if candidate.is_absolute() else None
    if folder is None or not folder.is_dir():
        raise ValueError(f"pasta não encontrada: {target}")
    runner(["explorer.exe", str(folder)])
    return f"Pasta aberta: {folder}"


def open_project(cfg, name: str, with_terminal: bool = False, runner=processos.abrir_visivel) -> str:
    from jarvis.dev import projects

    registered, folder = projects.resolve(cfg, name)
    code = shutil.which("code")
    if code:
        runner([code, str(folder)])
        opened = f"{registered} aberto no VS Code"
    else:
        runner(["explorer.exe", str(folder)])
        opened = f"{registered} aberto no Explorador (VS Code não encontrado)"
    if with_terminal and shutil.which("wt"):
        runner(["wt", "-d", str(folder)])
        opened += " e no Terminal"
    return opened + "."

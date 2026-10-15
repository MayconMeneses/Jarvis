"""Leituras do PC. Nada aqui altera o sistema."""

from __future__ import annotations

import os
import time
from pathlib import Path

import psutil

GB = 1024**3
MB = 1024**2


def overview() -> dict:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    info = {
        "cpu_uso_percent": psutil.cpu_percent(interval=0.5),
        "cpu_nucleos": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(),
        "ram_total_gb": round(mem.total / GB, 1),
        "ram_em_uso_percent": mem.percent,
        "ram_livre_gb": round(mem.available / GB, 1),
        "memoria_virtual_em_uso_percent": swap.percent,
        "disco_c_total_gb": round(disk.total / GB),
        "disco_c_livre_gb": round(disk.free / GB, 1),
        "disco_c_em_uso_percent": disk.percent,
        "ligado_ha_horas": round((time.time() - psutil.boot_time()) / 3600, 1),
        "processos_abertos": len(psutil.pids()),
    }
    battery = psutil.sensors_battery()
    if battery is not None:
        info["bateria_percent"] = battery.percent
        info["na_tomada"] = battery.power_plugged
    return info


def top_processes(sort_by: str = "memoria", limit: int = 10) -> list[dict]:
    """Processos agrupados por nome (o Chrome abre dezenas, por exemplo)."""
    procs = list(psutil.process_iter(["pid", "name", "memory_info"]))
    for p in procs:  # a 1ª leitura de CPU por processo sempre retorna 0
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    time.sleep(0.5)
    threads = psutil.cpu_count() or 1

    groups: dict[str, dict] = {}
    for p in procs:
        try:
            name = p.info["name"] or "?"
            mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
            cpu = p.cpu_percent(None) / threads
        except psutil.Error:
            continue
        if p.pid == 0:  # "System Idle Process" não é consumo real
            continue
        g = groups.setdefault(name, {"nome": name, "instancias": 0, "memoria_mb": 0.0,
                                      "cpu_percent": 0.0, "pids": []})
        g["instancias"] += 1
        g["memoria_mb"] += mem / MB
        g["cpu_percent"] += cpu
        g["pids"].append(p.pid)

    key = "cpu_percent" if sort_by == "cpu" else "memoria_mb"
    ranked = sorted(groups.values(), key=lambda g: g[key], reverse=True)[: max(1, min(limit, 30))]
    for g in ranked:
        g["memoria_mb"] = round(g["memoria_mb"])
        g["cpu_percent"] = round(g["cpu_percent"], 1)
        g["pids"] = g["pids"][:10]
    return ranked


def folder_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def disk_summary() -> dict:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = {
        "temporarios_usuario": Path(os.environ.get("TEMP", "")),
        "temporarios_windows": Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp",
        "cache_npm": local / "npm-cache",
        "cache_pip": local / "pip" / "cache",
        "downloads": Path.home() / "Downloads",
    }
    sizes = {
        name: round(folder_size(path) / GB, 2)
        for name, path in candidates.items()
        if str(path) and path.exists()
    }
    disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    return {"disco_c_livre_gb": round(disk.free / GB, 1), "pastas_gb": sizes}

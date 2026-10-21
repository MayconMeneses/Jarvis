"""Tailscale: liga o celular ao PC de qualquer lugar (4G, outro Wi-Fi), sem abrir portas e sem expor nada na internet.

O Tailscale cria uma rede privada entre os SEUS aparelhos (grátis para uso pessoal). Aqui a Jarvis só lê o estado dele e pede o
certificado HTTPS (que também libera o microfone e o service worker no iPhone). Nada é instalado nem configurado por aqui.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from jarvis import proc as processos
from jarvis.config import data_dir

CANDIDATOS = (r"C:\Program Files\Tailscale\tailscale.exe", r"C:\Program Files (x86)\Tailscale\tailscale.exe")
INSTALAR = ("Instale o Tailscale (gratuito, tailscale.com/download) no PC e no iPhone, entre nos dois com a MESMA conta e, no site "
            "login.tailscale.com/admin/dns, ligue \"MagicDNS\" e \"HTTPS Certificates\". Depois ligue o \"Jarvis no celular\" de novo.")


def achar() -> str | None:
    return shutil.which("tailscale") or next((c for c in CANDIDATOS if os.path.isfile(c)), None)


def estado(rodar=processos.executar) -> dict:
    """{"instalado", "ligado", "nome", "ip"}: o endereço deste PC dentro da rede Tailscale (nome vazio se não houver)."""
    exe = achar()
    vazio = {"instalado": exe is not None, "ligado": False, "nome": "", "ip": ""}
    if exe is None:
        return vazio
    try:
        saida = rodar([exe, "status", "--json"], capture_output=True, text=True, timeout=10)
        dados = json.loads(saida.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return vazio
    eu = dados.get("Self") or {}
    ips = [ip for ip in eu.get("TailscaleIPs", []) if "." in ip]  # IPv4 (100.x.y.z)
    if dados.get("BackendState") != "Running" or not ips:
        return vazio
    return {"instalado": True, "ligado": True, "nome": str(eu.get("DNSName", "")).rstrip("."), "ip": ips[0]}


def certificado(nome: str, pasta: Path | None = None, rodar=processos.executar) -> tuple[str, str]:
    """Pede o certificado HTTPS do nome *.ts.net ao Tailscale. Levanta OSError com o motivo se não conseguir."""
    exe = achar()
    if exe is None or not nome:
        raise OSError("Tailscale indisponível")
    pasta = pasta or data_dir() / "celular"
    pasta.mkdir(parents=True, exist_ok=True)
    cert, chave = pasta / f"{nome}.crt", pasta / f"{nome}.key"
    try:
        saida = rodar([exe, "cert", "--cert-file", str(cert), "--key-file", str(chave), nome], capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OSError(f"não consegui o certificado HTTPS ({exc})") from exc
    if saida.returncode != 0 or not cert.is_file() or not chave.is_file():
        raise OSError("o Tailscale não gerou o certificado HTTPS (ligue \"HTTPS Certificates\" no painel de DNS do Tailscale)")
    return str(cert), str(chave)

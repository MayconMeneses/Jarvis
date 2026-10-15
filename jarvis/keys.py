"""Chaves de API guardadas no Gerenciador de Credenciais do Windows.

Ordem de busca: variável de ambiente (ex.: GEMINI_API_KEY) e depois o cofre.
Nunca grava chave em arquivo de configuração.
"""

from __future__ import annotations

import os

import keyring

SERVICE = "SuperJarvis"
ENV_NAMES = {"gemini": "GEMINI_API_KEY", "nvidia": "NVIDIA_API_KEY", "brave": "BRAVE_API_KEY"}


def get_key(provider: str) -> str | None:
    env = ENV_NAMES.get(provider)
    if env and os.environ.get(env):
        return os.environ[env]
    try:
        return keyring.get_password(SERVICE, provider)
    except keyring.errors.KeyringError:
        return None


def set_key(provider: str, key: str) -> None:
    keyring.set_password(SERVICE, provider, key.strip())


def delete_key(provider: str) -> None:
    try:
        keyring.delete_password(SERVICE, provider)
    except keyring.errors.PasswordDeleteError:
        pass

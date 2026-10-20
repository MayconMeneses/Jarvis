"""Perfis de custo do Claude: econômico, equilibrado e máximo.

Cada perfil aponta para um modelo guardado em dados editáveis (config.perfis_modelo). Vazio = o modelo padrão da
assinatura (ou o de claude.model). Nenhum id é fixado aqui: SUGESTOES é só um ponto de partida que o usuário confirma.
"""

from __future__ import annotations

from dataclasses import replace

from jarvis.config import ClaudeConfig, Config

PERFIS = ("economico", "equilibrado", "maximo")
SUGESTOES = {"economico": "claude-haiku-5-5", "equilibrado": "claude-sonnet-5-5", "maximo": "claude-opus-5-5"}  # confirmar com o claude CLI do plano


def modelo_do_perfil(cfg: Config) -> str:
    return str(cfg.perfis_modelo.get(cfg.perfil_modelo, "")).strip()


def claude_config(cfg: Config) -> ClaudeConfig:
    """ClaudeConfig com o modelo do perfil escolhido (se o perfil tiver um); senão, o que já estava."""
    modelo = modelo_do_perfil(cfg)
    return replace(cfg.claude, model=modelo) if modelo else cfg.claude


def definir(cfg: Config, perfil: str, modelo: str | None = None) -> None:
    """Escolhe o perfil e, se vier `modelo`, grava nele (vazio limpa). Quem chama salva o config."""
    if perfil not in PERFIS:
        raise ValueError(f"perfil inválido: {perfil!r}. Use: {', '.join(PERFIS)}")
    cfg.perfil_modelo = perfil
    if modelo is not None:
        cfg.perfis_modelo = {**cfg.perfis_modelo, perfil: modelo.strip()}

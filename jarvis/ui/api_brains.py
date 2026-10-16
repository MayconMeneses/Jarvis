"""Painel de cérebros: cadastro e teste de chaves, status e regra de uso do Gemini."""

from __future__ import annotations

import logging

from jarvis import config

log = logging.getLogger(__name__)


class BrainsMixin:
    """Painel ⚙ Cérebros: chaves, status e quando usar o Gemini."""

    def brains_status(self) -> dict:
        import shutil

        from jarvis import keys

        cfg = config.load()
        return {
            "claude": bool(shutil.which(cfg.claude.executable)),
            "gemini": bool(keys.get_key("gemini")),
            "nvidia": bool(keys.get_key("nvidia")),
            "brave": bool(keys.get_key("brave")),
            "uso_gemini": cfg.uso_gemini,
            "modelo_gemini": cfg.gemini.model,
        }

    def save_key(self, provider: str, key: str) -> dict:
        """Testa a chave com uma pergunta mínima e só guarda se funcionar (nunca devolve a chave)."""
        from jarvis import keys
        from jarvis.brains.base import BrainUnavailable
        from jarvis.brains.openai_compat import OpenAICompat

        provider = str(provider)
        key = "".join(str(key).split())  # tira espaços e quebras de linha coladas junto
        if provider not in keys.ENV_NAMES:
            return {"ok": False, "mensagem": "provedor inválido"}
        if len(key) < 20:
            return {"ok": False, "mensagem": "isso não parece uma chave de API (muito curta)"}
        log.info("testando chave do %s (%d caracteres, início %s…)", provider, len(key), key[:4])
        if provider == "brave":  # buscador (não é IA): testa uma busca
            from jarvis.local import websearch

            try:
                websearch.brave("teste", key, limit=1)
            except Exception as exc:
                log.info("chave do brave recusada: %s", exc)
                return {"ok": False, "mensagem": f"A chave não funcionou: {exc}"}
            keys.set_key("brave", key)
            return {"ok": True, "mensagem": "Chave do Brave testada e guardada: busca completa na web sem IA ativada."}
        try:
            cfg = config.load()
            provider_cfg = getattr(cfg, provider)
            brain = OpenAICompat(provider, provider_cfg, lambda _name: key)
            test = [{"role": "user", "content": "Responda apenas: ok"}]
            try:
                brain.ask(test, "Teste de conexão.")
            except BrainUnavailable as exc:
                log.info("teste do %s com o modelo %s: %s", provider, provider_cfg.model, exc)
                if not str(exc).startswith("modelo não encontrado"):
                    return {"ok": False, "mensagem": f"A chave não funcionou: {exc}"}
                # A chave foi aceita, mas o nome do modelo não existe mais: escolhe um disponível.
                provider_cfg.model = pick_model(brain.list_models(), provider)
                log.info("modelo do %s trocado para %s", provider, provider_cfg.model)
                brain.ask(test, "Teste de conexão.")
                config.save(cfg)
            keys.set_key(provider, key)
        except (BrainUnavailable, ValueError) as exc:
            log.info("chave do %s recusada: %s", provider, exc)
            return {"ok": False, "mensagem": f"A chave não funcionou: {exc}"}
        except Exception as exc:  # nunca deixa o botão preso sem resposta
            log.exception("erro inesperado ao salvar a chave do %s", provider)
            return {"ok": False, "mensagem": f"Erro inesperado ao salvar: {exc}"}
        log.info("chave do %s guardada (modelo %s)", provider, provider_cfg.model)
        return {"ok": True, "mensagem": f"Chave do {provider.capitalize()} testada e guardada no cofre do "
                                        f"Windows (modelo {provider_cfg.model})."}

    def remove_key(self, provider: str) -> dict:
        from jarvis import keys

        if str(provider) in keys.ENV_NAMES:
            keys.delete_key(str(provider))
        return {"ok": True}

    def set_gemini_mode(self, mode: str) -> dict:
        from jarvis.brains import policy

        if mode not in policy.MODES:
            return {"ok": False}
        cfg = config.load()
        cfg.uso_gemini = mode
        config.save(cfg)
        return {"ok": True}


def pick_model(models: list[str], provider: str) -> str:
    """Modelo de texto rápido mais recente da lista (Gemini: "flash"; outros: o 1º de chat)."""
    import re

    skip = ("lite", "image", "tts", "audio", "live", "embedding", "vision", "thinking", "exp")
    if provider == "gemini":
        candidates = [m for m in models if "gemini" in m and "flash" in m and not any(s in m for s in skip)]
        if candidates:
            def version(name: str) -> tuple:
                found = re.search(r"(\d+(?:\.\d+)?)", name)
                return (float(found.group(1)) if found else 0.0, "preview" not in name, name)
            return max(candidates, key=version)
    chat = [m for m in models if not any(s in m for s in skip)]
    if not chat:
        raise ValueError("nenhum modelo de texto disponível para esta chave")
    return chat[0]

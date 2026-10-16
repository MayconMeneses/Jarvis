"""Fala com um servidor de modelo compatível com OpenAI (llama-server, Ollama, LM Studio) em 127.0.0.1."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from jarvis.brains.base import BrainUnavailable


def conversar(base_url: str, mensagens: list[dict], max_tokens: int = 700, temperatura: float = 0.4,
              timeout: int = 600, modelo: str = "local") -> str:
    corpo = {"model": modelo, "messages": mensagens, "max_tokens": max_tokens, "temperature": temperatura}
    pedido = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(corpo).encode("utf-8"),
                                    headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        return (dados["choices"][0]["message"]["content"] or "").strip()
    except urllib.error.HTTPError as exc:
        raise BrainUnavailable(f"o modelo local recusou o pedido (HTTP {exc.code})") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BrainUnavailable(f"o modelo local não respondeu ({exc})") from exc
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise BrainUnavailable("resposta inválida do modelo local") from exc


def no_ar(base_url: str, timeout: float = 2) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/health", timeout=timeout) as resposta:
            return resposta.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False

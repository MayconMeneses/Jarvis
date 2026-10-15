"""Cérebros com API compatível com OpenAI: Gemini (AI Studio) e NVIDIA NIM.

Usa só a biblioteca padrão, sem SDKs extras.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable

from jarvis.brains.base import Answer, BrainUnavailable, Message
from jarvis.config import ProviderConfig

log = logging.getLogger(__name__)


class OpenAICompat:
    def __init__(
        self, name: str, cfg: ProviderConfig, get_key: Callable[[str], str | None]
    ) -> None:
        self.name = name
        self.cfg = cfg
        self._get_key = get_key

    def ask(self, messages: list[Message], system: str) -> Answer:
        key = self._get_key(self.name)
        if not key:
            raise BrainUnavailable("sem chave de API configurada")

        body = {
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        request = urllib.request.Request(
            self.cfg.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.cfg.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            log.warning("%s HTTP %s: %s", self.name, exc.code, detail)
            reason = {401: "chave inválida", 403: "acesso negado", 429: "limite de uso atingido"}
            raise BrainUnavailable(reason.get(exc.code, f"erro HTTP {exc.code}")) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BrainUnavailable(f"sem conexão ({exc})") from exc
        except json.JSONDecodeError as exc:
            raise BrainUnavailable("resposta inválida") from exc

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise BrainUnavailable("resposta sem conteúdo") from exc
        return Answer(text=text.strip(), brain=self.name)

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


def http_reason(name: str, exc: urllib.error.HTTPError) -> str:
    """Motivo legível de um erro HTTP, usando a mensagem do próprio provedor quando houver."""
    body = exc.read().decode("utf-8", "replace")
    log.warning("%s HTTP %s: %s", name, exc.code, body[:300])
    message = ""
    try:
        data = json.loads(body)
        error = (data[0] if isinstance(data, list) else data).get("error", {})
        message = str(error.get("message", "") if isinstance(error, dict) else error)
    except (ValueError, AttributeError, IndexError):
        pass
    low = message.lower()
    if exc.code in (401, 403) or "api key" in low or "api_key" in low:
        return f"chave inválida ({message or 'recusada pelo provedor'})"
    if exc.code == 429:
        return f"limite de uso atingido ({message})" if message else "limite de uso atingido"
    # 410 Gone / "end of life": o provedor aposentou o modelo (a NVIDIA faz isso com frequência); a chave está certa.
    if exc.code in (404, 410) or any(t in low for t in ("not found", "is not supported", "end of life", "eol", "deprecated", "retired")):
        return f"modelo não encontrado (HTTP {exc.code}: {message})"
    return f"erro HTTP {exc.code}" + (f": {message}" if message else "")


class OpenAICompat:
    def __init__(
        self, name: str, cfg: ProviderConfig, get_key: Callable[[str], str | None]
    ) -> None:
        self.name = name
        self.cfg = cfg
        self._get_key = get_key

    def list_models(self) -> list[str]:
        """Modelos disponíveis para a chave (GET /models), sem o prefixo "models/"."""
        key = self._get_key(self.name)
        if not key:
            raise BrainUnavailable("sem chave de API configurada")
        request = urllib.request.Request(
            self.cfg.base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.cfg.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise BrainUnavailable(http_reason(self.name, exc)) from exc
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise BrainUnavailable(f"não foi possível listar os modelos ({exc})") from exc
        return [str(m.get("id", "")).removeprefix("models/") for m in data.get("data", []) if m.get("id")]

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
            raise BrainUnavailable(http_reason(self.name, exc)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BrainUnavailable(f"sem conexão ({exc})") from exc
        except json.JSONDecodeError as exc:
            raise BrainUnavailable("resposta inválida") from exc

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise BrainUnavailable("resposta sem conteúdo") from exc
        return Answer(text=text.strip(), brain=self.name)

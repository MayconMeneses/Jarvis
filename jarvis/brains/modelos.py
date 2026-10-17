"""Escolha de modelo de conversa para provedores com catálogo que muda (NVIDIA NIM).

O catálogo da NVIDIA mistura modelos de conversa com embeddings, moderação, visão, voz e tradução, e retira modelos de tempos
em tempos. Aqui ficam: os preferidos (conversa de texto, estáveis), o que nunca serve para conversa e a ordem de tentativa.
"""

from __future__ import annotations

PREFERIDOS_NVIDIA = (
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "nvidia/llama-3.1-nemotron-51b-instruct",
    "google/gemma-3-12b-it",
    "nv-mistralai/mistral-nemo-12b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "deepseek-ai/deepseek-v4.1-flash",
    "z-ai/glm-5.3-flash",
)
# Pedaços de nome de modelos que NÃO são de conversa de texto (ou que raciocinam em voz alta e atrapalham respostas curtas).
NAO_SERVE = ("embed", "guard", "safety", "reward", "parse", "vlm", "vision", "vila", "neva", "nvclip", "riva", "deplot", "fuyu", "kosmos",
             "retriev", "calibration", "detector", "cosmos", "topic-control", "diffusion", "starcoder", "codegemma", "codellama",
             "coder", "reasoning", "lite", "image", "tts", "audio", "live", "thinking", "exp", "preview", "-base", "rerank", "translate")


def candidatos(modelos: list[str]) -> list[str]:
    """Modelos de conversa, na ordem em que vale tentar: preferidos primeiro, depois os outros "instruct"/"chat" e o resto."""
    uteis = [m for m in modelos if not any(p in m.lower() for p in NAO_SERVE)]
    preferidos = [m for m in PREFERIDOS_NVIDIA if m in uteis]
    resto = [m for m in uteis if m not in preferidos]
    resto.sort(key=lambda m: (not any(p in m.lower() for p in ("instruct", "chat", "-it")), m))
    return preferidos + resto

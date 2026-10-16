"""Modelos recomendados para PC fraco, caminhos dos arquivos e estado da instalação."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from jarvis.config import data_dir


@dataclass(frozen=True)
class Modelo:
    id: str
    nome: str
    repo: str           # repositório no Hugging Face
    arquivo: str        # arquivo GGUF (quantização Q4_K_M: bom equilíbrio entre tamanho e qualidade)
    mb: int             # tamanho aproximado do download
    ram_gb: float       # memória aproximada para rodar
    descricao: str

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo}/resolve/main/{self.arquivo}"


MODELOS = {
    "qwen2.5-coder-1.5b": Modelo("qwen2.5-coder-1.5b", "Qwen2.5 Coder 1,5B", "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
                                 "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf", 1100, 2.5,
                                 "Rápido e bom em código; o recomendado para PC com 8 GB de memória."),
    "qwen2.5-coder-3b": Modelo("qwen2.5-coder-3b", "Qwen2.5 Coder 3B", "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
                               "qwen2.5-coder-3b-instruct-q4_k_m.gguf", 2000, 4.0,
                               "Melhor em código que o 1,5B; para aparelhos com 12 GB de memória ou mais."),
    "qwen2.5-coder-7b": Modelo("qwen2.5-coder-7b", "Qwen2.5 Coder 7B", "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                               "qwen2.5-coder-7b-instruct-q4_k_m.gguf", 4700, 7.5,
                               "O mais capaz da lista; para aparelhos com 28 GB de memória ou mais (ou com placa de vídeo)."),
    "qwen2.5-3b": Modelo("qwen2.5-3b", "Qwen2.5 3B", "Qwen/Qwen2.5-3B-Instruct-GGUF",
                         "qwen2.5-3b-instruct-q4_k_m.gguf", 2100, 4.0,
                         "Conversa e raciocina melhor, mas é umas 2 vezes mais lento."),
}
PADRAO = "qwen2.5-coder-1.5b"
MOTOR_ZIP = re.compile(r"^llama-.+-bin-win-cpu-x64\.zip$")
MOTOR_MB = 20


def raiz() -> Path:
    return data_dir() / "llm"


def _embutido() -> Path:
    from jarvis.voice.models import bundled_root

    return bundled_root() / "llm"


def modelo(id_: str) -> Modelo:
    if id_ == "auto":  # o melhor para ESTE aparelho (mais memória e processador = modelo maior)
        from jarvis.llm import perfil

        id_ = perfil.recomendado()
    if id_ not in MODELOS:
        raise ValueError(f"modelo desconhecido: {id_} (use {', '.join(MODELOS)})")
    return MODELOS[id_]


def caminho_modelo(id_: str) -> Path | None:
    item = modelo(id_)
    for base in (_embutido(), raiz()):
        achado = base / "modelos" / item.arquivo
        if achado.is_file():
            return achado
    return None


def caminho_motor() -> Path | None:
    for base in (_embutido(), raiz()):
        achado = next((base / "motor").rglob("llama-server.exe"), None) if (base / "motor").is_dir() else None
        if achado:
            return achado
    return None


def estado(id_: str, endpoint: str = "") -> dict:
    """O que já está instalado e quanto falta baixar (em MB aproximados)."""
    item = modelo(id_)
    tem_motor, tem_modelo = caminho_motor() is not None, caminho_modelo(item.id) is not None
    externo = bool(endpoint.strip())
    return {"modelo": item.id, "nome": item.nome, "motor": tem_motor, "arquivo": tem_modelo, "externo": externo,
            "pronto": externo or (tem_motor and tem_modelo),
            "falta_mb": 0 if externo else (0 if tem_motor else MOTOR_MB) + (0 if tem_modelo else item.mb)}

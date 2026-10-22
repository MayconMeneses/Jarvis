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
    sha256: str = ""    # impressão digital do arquivo no Hugging Face: o download é descartado se não bater
    bytes: int = 0      # tamanho exato (confere com o download)
    licenca: str = ""
    conversa: bool = False     # ajustado para conversa geral (os "Coder" são para código)
    tps: float = 0.0           # tokens/s medidos neste tipo de PC (i5 de 4 núcleos, 8 GB, sem GPU); 0 = não medido
    sem_pensar: bool = False   # modelo híbrido: desliga o "pensar" longo (lento demais neste tipo de PC)

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo}/resolve/main/{self.arquivo}"


MODELOS = {
    "qwen2.5-coder-1.5b": Modelo("qwen2.5-coder-1.5b", "Qwen2.5 Coder 1,5B", "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
                                 "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf", 1100, 2.5,
                                 "Rápido e bom em código; o recomendado para PC com 8 GB de memória.",
                                 "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046", 1117320768, "Apache-2.0", tps=10.6),
    "qwen2.5-coder-3b": Modelo("qwen2.5-coder-3b", "Qwen2.5 Coder 3B", "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
                               "qwen2.5-coder-3b-instruct-q4_k_m.gguf", 2000, 4.0,
                               "Melhor em código que o 1,5B; para aparelhos com 12 GB de memória ou mais.",
                               "724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7", 2104932800, "Qwen Research (uso não comercial)"),
    "qwen2.5-coder-7b": Modelo("qwen2.5-coder-7b", "Qwen2.5 Coder 7B", "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                               "qwen2.5-coder-7b-instruct-q4_k_m.gguf", 4700, 7.5,
                               "O mais capaz da lista; para aparelhos com 28 GB de memória ou mais (ou com placa de vídeo).",
                               "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c", 4683073536, "Apache-2.0"),
    "qwen2.5-3b": Modelo("qwen2.5-3b", "Qwen2.5 3B", "Qwen/Qwen2.5-3B-Instruct-GGUF",
                         "qwen2.5-3b-instruct-q4_k_m.gguf", 2100, 4.0,
                         "Conversa e raciocina melhor, mas é umas 2 vezes mais lento.",
                         "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d", 2104932768, "Qwen Research (uso não comercial)"),
    "qwen3-4b": Modelo("qwen3-4b", "Qwen3 4B Instruct (conversa)", "unsloth/Qwen3-4B-Instruct-2507-GGUF",
                       "Qwen3-4B-Instruct-2507-Q4_K_M.gguf", 2382, 3.6,
                       "Cérebro local melhor para CONVERSAR: respostas mais completas e corretas em português. "
                       "Em compensação é bem mais lento que o 1,5B.",
                       "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597", 2497281120, "Apache-2.0", conversa=True, tps=3.9),
    "qwen3-1.7b": Modelo("qwen3-1.7b", "Qwen3 1,7B (conversa rápida)", "unsloth/Qwen3-1.7B-GGUF",
                         "Qwen3-1.7B-Q4_K_M.gguf", 1056, 2.2,
                         "Conversa em português com a velocidade do 1,5B (modo \"pensar\" desligado).",
                         "b139949c5bd74937ad8ed8c8cf3d9ffb1e99c866c823204dc42c0d91fa181897", 1107409472, "Apache-2.0",
                         conversa=True, sem_pensar=True, tps=9.1),
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

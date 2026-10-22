"""Parâmetros do llama-server ajustados à CPU (sem placa de vídeo), medidos num i5-8265U de 4 núcleos e 8 GB.

Regras que saíram da medição (docs/CEREBRO-LOCAL.md):
- threads = núcleos FÍSICOS: com os 8 lógicos a geração ficou mais lenta (6,8 contra 8,8 tokens/s), pois a
  geração depende da largura de banda da memória e os pares de hyper-threading só disputam o mesmo núcleo;
- um só "slot" (-np 1): o contexto inteiro serve a conversa e o cache do prompt do sistema é reaproveitado;
- sem mlock e com mmap: o Windows pode devolver a memória se o usuário abrir outros programas;
- cache de prompt (--cache-reuse): a persona e as instruções repetem em toda pergunta e não são recalculadas.
"""

from __future__ import annotations

import os

CONTEXTO = 4096     # persona (~1000 tokens) + 6 mensagens de histórico + 700 de resposta cabem folgado
LOTE = 512          # prompt processado em blocos de 512: mais que isso só gasta memória neste processador
REUSO_CACHE = 256


def nucleos_fisicos() -> int:
    try:
        import psutil

        return max(1, psutil.cpu_count(logical=False) or (os.cpu_count() or 2) // 2)
    except Exception:
        return max(1, (os.cpu_count() or 2) // 2)


def argumentos(porta: int, caminho_modelo: str, item=None, nucleos: int | None = None) -> list[str]:
    """Argumentos do llama-server (sem o executável) para `item` (um catalogo.Modelo; None = modelo comum)."""
    n = nucleos or nucleos_fisicos()
    args = ["-m", caminho_modelo, "--host", "127.0.0.1", "--port", str(porta), "-c", str(CONTEXTO),
            "-t", str(n), "-tb", str(n), "-b", str(LOTE), "-ub", str(LOTE), "-np", "1",
            "--cache-reuse", str(REUSO_CACHE), "--no-webui"]
    if item is not None and getattr(item, "sem_pensar", False):
        args += ["-rea", "off"]
    return args

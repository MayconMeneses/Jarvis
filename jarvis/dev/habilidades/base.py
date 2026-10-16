"""Peças comuns das checagens: o resultado de cada uma e dois ajudantes."""

from __future__ import annotations

from dataclasses import dataclass, field

from jarvis.dev.habilidades.varredura import Projeto, eh_modelo, eh_teste


@dataclass
class Resultado:
    nota: int | None
    achados: list[str] = field(default_factory=list)
    sugestoes: list[str] = field(default_factory=list)


def limitar(valor: float) -> int:
    return max(0, min(100, round(valor)))


def codigo_de(p: Projeto, incluir_testes: bool = False) -> dict[str, str]:
    """Texto do código-fonte (sem HTML/CSS/SQL, modelos de exemplo e, por padrão, sem testes)."""
    return {c: t for c, t in p.textos.items() if not eh_modelo(c) and (incluir_testes or not eh_teste(c))
            and not c.endswith((".html", ".css", ".sql"))}

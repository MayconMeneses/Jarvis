"""Cálculos de design: contraste WCAG, paleta a partir de uma cor, escala tipográfica, espaçamento e tokens CSS."""

from __future__ import annotations

import colorsys
import re


def para_rgb(cor: str) -> tuple[int, int, int]:
    """#rgb ou #rrggbb (com ou sem #) → (r, g, b). Levanta ValueError se não for uma cor hexadecimal."""
    hexa = cor.strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", hexa):
        hexa = "".join(c * 2 for c in hexa)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hexa):
        raise ValueError(f"cor inválida: {cor!r} (use #rgb ou #rrggbb)")
    return int(hexa[0:2], 16), int(hexa[2:4], 16), int(hexa[4:6], 16)


def luminancia(cor: str) -> float:
    def canal(v: int) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(v) for v in para_rgb(cor))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    claro, escuro = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def avaliar_contraste(texto: str, fundo: str) -> str:
    razao = contraste(texto, fundo)
    ok = lambda minimo: "passa" if razao >= minimo else "FALHA"  # noqa: E731
    return (f"**Contraste {texto} sobre {fundo}: {razao:.2f}:1**\n"
            f"- Texto normal (AA, mínimo 4,5:1): {ok(4.5)}\n- Texto grande (AA, mínimo 3:1): {ok(3)}\n"
            f"- Texto normal (AAA, mínimo 7:1): {ok(7)}\n- Componentes de interface e ícones (mínimo 3:1): {ok(3)}")


def para_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(round(max(0, min(1, v)) * 255) for v in (r, g, b)))


def paleta(cor: str) -> dict[str, str]:
    """Tons 50–900 da mesma matiz (do mais claro ao mais escuro), no estilo dos design systems."""
    h, _, s = colorsys.rgb_to_hls(*(v / 255 for v in para_rgb(cor)))
    tons = {50: 0.96, 100: 0.92, 200: 0.84, 300: 0.74, 400: 0.62, 500: 0.50, 600: 0.42, 700: 0.34, 800: 0.26, 900: 0.18}
    return {str(nome): para_hex(*colorsys.hls_to_rgb(h, luz, s)) for nome, luz in tons.items()}


def escala_tipografica(base: float = 16, razao: float = 1.25, passos: int = 6) -> list[tuple[str, float]]:
    """Tamanhos em px: dois abaixo da base e `passos` acima, multiplicando pela razão (1,25 = terça maior)."""
    nomes = ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl"]
    return [(nomes[i + 2], round(base * razao ** i, 2)) for i in range(-2, passos - 1)][: len(nomes)]


def escala_espacamento(base: int = 4, passos: int = 10) -> list[int]:
    """Múltiplos da unidade base (4px ou 8px), a grade que mantém o ritmo visual."""
    return [base * n for n in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24)[:passos]]


def tokens_css(cor_principal: str, base: float = 16, razao: float = 1.25) -> str:
    linhas = [":root {"]
    linhas += [f"  --cor-{nome}: {valor};" for nome, valor in paleta(cor_principal).items()]
    linhas += [f"  --texto-{nome}: {tamanho / 16:g}rem;" for nome, tamanho in escala_tipografica(base, razao)]
    linhas += [f"  --espaco-{i + 1}: {valor / 16:g}rem;" for i, valor in enumerate(escala_espacamento())]
    linhas += ["  --raio: 0.5rem;", "  --duracao: 200ms;", "}",
               "@media (prefers-color-scheme: dark) { :root { color-scheme: dark; } }",
               "@media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }"]
    return "\n".join(linhas)


def relatorio_paleta(cor: str) -> str:
    tons = paleta(cor)
    linhas = [f"**Paleta a partir de {cor}** (contraste do tom sobre branco / sobre preto):"]
    for nome, valor in tons.items():
        linhas.append(f"- {nome}: `{valor}` — {contraste(valor, '#ffffff'):.1f}:1 / {contraste(valor, '#000000'):.1f}:1")
    linhas.append("Dica: texto normal precisa de pelo menos 4,5:1; use tons 700–900 para texto sobre fundo claro.")
    return "\n".join(linhas)


def relatorio_escala(base: float = 16, razao: float = 1.25) -> str:
    tam = ", ".join(f"{n} {t:g}px" for n, t in escala_tipografica(base, razao))
    esp = ", ".join(f"{v}px" for v in escala_espacamento())
    return f"**Escala tipográfica (base {base:g}px, razão {razao:g}):** {tam}\n**Espaçamento (grade de 4px):** {esp}"

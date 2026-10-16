"""Modelos de projeto: sistemas iniciais prontos para rodar, criados a partir de arquivos reais.

Um modelo é a combinação de um back-end e/ou um front-end: "fastapi+react", "express+html",
"fastapi" (só API), "react" (só tela)... Cada peça vem de arquivos em arquivos/<peça>/ (extensão
.tpl, com __NOME__, __SLUG__ e __DESCRICAO__ trocados na criação) e já traz um exemplo completo
de CRUD com testes. Tudo é gerado sem IA e sem internet; depois o usuário (ou o Claude Code)
evolui o projeto a partir dele.

Contrato único entre qualquer back e qualquer front (por isso as 4 combinações funcionam):
GET/POST /api/itens, PATCH/DELETE /api/itens/{id}, GET /api/saude, API em http://localhost:8000.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from jarvis.dev.modelos.leiame import leiame

BASE = Path(__file__).parent / "arquivos"
BACKS = {"fastapi": "FastAPI (Python)", "express": "Express (Node.js)"}
FRONTS = {"react": "React (Vite)", "html": "HTML + CSS + JavaScript"}
_SINONIMOS = {
    "fast api": "fastapi", "python": "fastapi", "node": "express", "nodejs": "express", "node.js": "express",
    "expressjs": "express", "reactjs": "react", "vite": "react", "vanilla": "html", "js": "html",
    "javascript": "html", "css": "html", "html+css+js": "html",
}
# Peças que reaproveitam um arquivo de outra: (origem, destino)
_EXTRAS = {"react": [("front-html/frontend/styles.css.tpl", "frontend/src/styles.css")]}


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def parse(modelo: str) -> tuple[str, str]:
    """("fastapi+react") -> ("fastapi", "react"); "" no lado que não existe. Levanta ValueError se inválido."""
    parts = [p.strip() for p in re.split(r"\s*(?:\+|/|,|\se\s|\scom\s)\s*", _fold(modelo)) if p.strip()]
    back = front = ""
    for part in parts:
        part = _SINONIMOS.get(part, part)
        if part in BACKS and not back:
            back = part
        elif part in FRONTS and not front:
            front = part
        else:
            raise ValueError(f"não tenho um modelo pronto para \"{part}\". " + opcoes())
    if not back and not front:
        raise ValueError("diga a stack do modelo. " + opcoes())
    return back, front


def normalize(modelo: str) -> str:
    back, front = parse(modelo)
    return "+".join(p for p in (back, front) if p)


def opcoes() -> str:
    return (f"Back-end: {', '.join(BACKS)}. Front-end: {', '.join(FRONTS)}. "
            "Exemplos: \"fastapi+react\", \"express+html\", \"fastapi\" (só API).")


def descricao(modelo: str) -> str:
    back, front = parse(modelo)
    return " + ".join(x for x in (BACKS.get(back), FRONTS.get(front)) if x)


def slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _fold(nome)).strip("-") or "projeto"


def arquivos(modelo: str, nome: str, texto: str = "") -> dict[str, str]:
    """Caminho relativo -> conteúdo, sem tocar no disco."""
    back, front = parse(modelo)
    # Sem aspas, <>, {}, $ ou barras: o nome vai para HTML, JSX, JSON e docstrings sem quebrar nem injetar nada.
    seguro = re.sub(r"[<>&\"'`{}$\\]", "", nome).strip() or "Projeto"
    trocas = {"__NOME__": seguro, "__SLUG__": slug(nome), "__DESCRICAO__": texto.strip()}
    saida: dict[str, str] = {}

    def ler(origem: Path, destino: str) -> None:
        conteudo = origem.read_text(encoding="utf-8")
        for chave, valor in trocas.items():
            conteudo = conteudo.replace(chave, valor)
        saida[destino] = conteudo

    for peca in [p for p in (f"back-{back}" if back else "", f"front-{front}" if front else "", "raiz") if p]:
        for origem in sorted((BASE / peca).rglob("*.tpl")):
            destino = origem.relative_to(BASE / peca).as_posix().removesuffix(".tpl")
            ler(origem, destino.replace("gitignore", ".gitignore") if destino == "gitignore" else destino)  # sem ponto no pacote
    for peca, extras in _EXTRAS.items():
        if peca == front:
            for origem, destino in extras:
                ler(BASE / origem, destino)
    saida["README.md"] = leiame(nome.strip(), texto.strip(), back, front)
    return saida


def generate(target: Path, modelo: str, nome: str, texto: str = "") -> list[str]:
    """Escreve o modelo em `target` (pasta já criada). Devolve os arquivos criados."""
    files = arquivos(modelo, nome, texto)
    for relativo, conteudo in files.items():
        destino = target / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    return sorted(files)

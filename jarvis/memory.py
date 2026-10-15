"""Memória da Jarvis dentro do cofre do Obsidian do usuário.

    <cofre>/Jarvis/00 - Índice.md      índice gerado das memórias
    <cofre>/Jarvis/Memória/*.md        um fato por nota (o usuário pode editar ou apagar)
    <cofre>/Jarvis/Diário/AAAA-MM-DD.md o que foi pedido e feito no dia
    <cofre>/Jarvis/Relatórios/*.md     briefings e resumos

A Jarvis só ESCREVE dentro de Jarvis/. O resto do cofre é somente leitura.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

HOME = "Jarvis"
MEMORY_DIR = "Memória"
INDEX = "00 - Índice.md"
MAX_INDEX_CHARS = 2500
_FORBIDDEN = re.compile(r'[\\/:*?"<>|#^\[\]]')


def _fold(text: str) -> str:
    """Minúsculas e sem acentos, para buscas tolerantes."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, text[end + 4:].lstrip("\n")


class Vault:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.home = self.root / HOME

    @property
    def available(self) -> bool:
        return self.root.is_dir()

    def ensure(self) -> None:
        for sub in (MEMORY_DIR, "Diário", "Relatórios"):
            (self.home / sub).mkdir(parents=True, exist_ok=True)

    # ── memória ──────────────────────────────────────────────────────────
    def remember(self, title: str, fact: str, summary: str = "") -> Path:
        title = _FORBIDDEN.sub("", title).strip()[:80]
        fact = fact.strip()
        if not title or not fact:
            raise ValueError("título e fato são obrigatórios")
        self.ensure()
        path = self.home / MEMORY_DIR / f"{title}.md"
        today = date.today().isoformat()
        created = today
        if path.exists():
            created = _frontmatter(path.read_text(encoding="utf-8"))[0].get("criado", today)
        summary = (summary or fact.splitlines()[0])[:140].replace("\n", " ")
        path.write_text(
            f"---\ntipo: memoria\nresumo: {summary}\ncriado: {created}\natualizado: {today}\n---\n"
            f"# {title}\n\n{fact}\n",
            encoding="utf-8",
        )
        self.write_index()
        return path

    def memories(self) -> list[tuple[str, str]]:
        folder = self.home / MEMORY_DIR
        if not folder.is_dir():
            return []
        found = []
        for path in sorted(folder.glob("*.md")):
            meta, body = _frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            first = next((l.strip() for l in body.splitlines() if l.strip() and not l.startswith("#")), "")
            found.append((path.stem, meta.get("resumo") or first[:140]))
        return found

    def index_text(self) -> str:
        lines = [f"- {title}: {summary}" for title, summary in self.memories()]
        text = "\n".join(lines)
        return text[:MAX_INDEX_CHARS] + ("\n- (mais memórias no Obsidian)" if len(text) > MAX_INDEX_CHARS else "")

    def write_index(self) -> None:
        self.ensure()
        lines = [f"- [[{title}]] — {summary}" for title, summary in self.memories()]
        (self.home / INDEX).write_text(
            "# Memória da Jarvis\n\nGerado automaticamente. Edite ou apague as notas em "
            f"`{MEMORY_DIR}/` e a Jarvis passa a usar a versão nova.\n\n" + "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    # ── leitura do cofre (somente leitura) ───────────────────────────────
    def _inside(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or ".obsidian" in path.parts:
            raise ValueError("caminho fora do cofre")
        return path

    def search(self, query: str, limit: int = 8) -> list[dict]:
        terms = [t for t in _fold(query).split() if len(t) > 2]
        if not terms:
            return []
        results = []
        for path in self.root.rglob("*.md"):
            if ".obsidian" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            folded = _fold(text)
            score = sum(folded.count(t) for t in terms) + 5 * sum(t in _fold(path.stem) for t in terms)
            if score:
                pos = min((folded.find(t) for t in terms if t in folded), default=0)
                snippet = text[max(0, pos - 80): pos + 220].replace("\n", " ")
                results.append({"nota": str(path.relative_to(self.root)), "trecho": snippet, "_s": score})
        results.sort(key=lambda r: r["_s"], reverse=True)
        return [{k: v for k, v in r.items() if k != "_s"} for r in results[:limit]]

    def read(self, relative: str, max_chars: int = 8000) -> str:
        path = self._inside(relative)
        if path.suffix.lower() != ".md" or not path.is_file():
            raise ValueError("nota não encontrada")
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]

    # ── diário e relatórios ──────────────────────────────────────────────
    def diary(self, entry: str) -> None:
        self.ensure()
        path = self.home / "Diário" / f"{date.today().isoformat()}.md"
        if not path.exists():
            path.write_text(f"# Diário {date.today().strftime('%d/%m/%Y')}\n\n", encoding="utf-8")
        line = entry.strip().replace("\n", " ")[:300]
        with path.open("a", encoding="utf-8") as f:
            f.write(f"- {datetime.now().strftime('%H:%M')} — {line}\n")

    def save_report(self, name: str, content: str) -> Path:
        self.ensure()
        name = _FORBIDDEN.sub("", name).strip()[:80]
        path = self.home / "Relatórios" / f"{date.today().isoformat()} {name}.md"
        path.write_text(content, encoding="utf-8")
        return path


def open_vault(path: str) -> Vault | None:
    if not path:
        return None
    vault = Vault(Path(path))
    return vault if vault.available else None

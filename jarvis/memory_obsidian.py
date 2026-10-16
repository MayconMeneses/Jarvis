"""Obsidian é opcional: importar uma vez as notas de Jarvis/ e exportar uma cópia em Markdown.

`import_obsidian` só LÊ o cofre e nunca sobrescreve o que já está no banco. `export_markdown`
grava uma nota por arquivo (o banco continua sendo a fonte da verdade) e sobrescreve notas
de mesmo caminho.
"""

from __future__ import annotations

import re
from pathlib import Path

from jarvis.memory_db import INDEX_NAME, MEMORY_PREFIX, MemoryDB


def _split_frontmatter(text: str) -> tuple[dict, str]:
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


def import_obsidian(db: MemoryDB, vault_root: str | Path, home: str = "Jarvis") -> int:
    """Copia as notas de <cofre>/Jarvis/ que ainda não existem no banco. Só lê o cofre. Devolve quantas."""
    base = Path(vault_root) / home
    if not base.is_dir():
        return 0
    imported = 0
    for path in sorted(base.rglob("*.md")):
        if ".obsidian" in path.parts:
            continue
        rel = path.relative_to(base).with_suffix("")
        ref = "/".join(rel.parts)
        if ref == INDEX_NAME or db.exists(ref):
            continue
        try:
            meta, body = _split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            title = rel.parts[-1]
            if ref.startswith(MEMORY_PREFIX):  # a nota repete o título como "# Título"
                body = re.sub(rf"^#\s*{re.escape(title)}\s*\n+", "", body)
            db.put(ref, body.strip("\n") + "\n", meta.get("tipo", "nota"), meta.get("resumo", ""), title,
                   created=meta.get("criado", ""), updated=meta.get("atualizado", ""))
            imported += 1
        except (OSError, ValueError):
            continue
    return imported


def export_markdown(db: MemoryDB, folder: str | Path) -> int:
    """Grava uma cópia em Markdown (uma nota por arquivo) em `folder`. Sobrescreve as notas de mesmo caminho."""
    root = Path(folder).resolve()
    root.mkdir(parents=True, exist_ok=True)
    exported = 0
    with db._tx() as conn:
        rows = conn.execute("SELECT * FROM notas ORDER BY ref").fetchall()
    for row in rows:
        target = (root / (row["ref"] + ".md")).resolve()
        if not target.is_relative_to(root):
            continue
        front = [f"tipo: {row['tipo']}"]
        if row["resumo"]:
            front.append(f"resumo: {row['resumo']}")
        front += [f"criado: {row['criado'][:10]}", f"atualizado: {row['atualizado'][:10]}"]
        body = row["corpo"]
        if row["ref"].startswith(MEMORY_PREFIX):
            body = f"# {row['titulo']}\n\n{body}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("---\n" + "\n".join(front) + "\n---\n" + body.rstrip("\n") + "\n", encoding="utf-8")
        exported += 1
    lines = [f"- [[{t}]] — {s}" for t, s in db.memories()]
    (root / f"{INDEX_NAME}.md").write_text(
        "# Memória da Jarvis\n\nCópia gerada automaticamente: o banco da Jarvis é a fonte da verdade.\n\n"
        + "\n".join(lines) + "\n", encoding="utf-8")
    return exported

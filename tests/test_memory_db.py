import threading

import pytest

from jarvis import memory_db, memory_obsidian
from jarvis.config import Config
from jarvis.memory_db import MemoryDB


@pytest.fixture
def db(tmp_path):
    return MemoryDB(tmp_path / "dados" / "memoria.db")


def test_remember_updates_same_title_and_keeps_creation_date(db):
    ref = db.remember("Stack", "Usa Python.")
    assert ref == "Memória/Stack"
    first = db.list_notes("Memória/")[0]
    db.remember("Stack", "Usa Python e TypeScript.")
    [note] = db.list_notes("Memória/")
    assert note["criado"] == first["criado"] and db.read(ref) == "Usa Python e TypeScript."
    assert db.index_text() == "- Stack: Usa Python e TypeScript."
    assert len(db.memories()) == 1


def test_index_is_sorted_and_capped(db):
    db.remember("B", "segundo")
    db.remember("A", "primeiro", "resumo curto")
    assert db.index_text().splitlines() == ["- A: resumo curto", "- B: segundo"]
    for i in range(40):
        db.remember(f"Assunto {i:03d}", "x" * 100)
    text = db.index_text()
    assert len(text) < memory_db.MAX_INDEX_CHARS + 60 and text.endswith("(mais memórias guardadas)")


def test_titles_cannot_escape_or_be_empty(db):
    assert db.remember("../../fora", "x") == "Memória/fora"
    assert memory_db.clean_ref("..\\..\\a/./b") == "a/b"
    with pytest.raises(ValueError):
        db.remember("///", "x")
    with pytest.raises(ValueError):
        db.remember("Titulo", "   ")
    with pytest.raises(ValueError):
        memory_db.clean_ref("../..")


def test_search_ignores_accents_case_and_ranks_title_hits_first(db):
    db.remember("Ação", "Revisar orçamento do cliente")
    db.put("Projetos/Loja/Sobre", "Tela de login com Postgres", "projeto")
    assert [h["nota"] for h in db.search("ACAO orcamento")] == ["Memória/Ação"]
    hits = db.search("postgres logins")  # prefixo: "logins" não casa, "postgres" sim
    assert [h["nota"] for h in hits] == ["Projetos/Loja/Sobre"] and "Postgres" in hits[0]["trecho"]
    assert db.search("de") == [] and db.search("") == []
    assert db.search('"; DROP TABLE notas; --') == [] and db.count() == 2  # entrada hostil é inofensiva


def test_read_get_delete_and_missing_notes(db):
    db.put("Perfil Profissional", "Stack: Python")
    assert db.read("Perfil Profissional") == "Stack: Python" and db.exists("perfil profissional") is False
    assert db.delete("Perfil Profissional") is True and db.delete("Perfil Profissional") is False
    assert db.search("python") == []  # saiu do índice de busca também
    with pytest.raises(ValueError, match="não encontrada"):
        db.read("Perfil Profissional")


def test_diary_appends_timestamped_lines(db):
    db.diary("Pedido: clima\ncom quebra")
    db.diary("Ação executada")
    [note] = db.list_notes("Diário/")
    lines = db.read(note["ref"]).splitlines()
    assert lines[0].startswith("# Diário") and lines[-2].endswith("Pedido: clima com quebra")
    assert lines[-1].endswith("Ação executada")


def test_reports_are_saved_with_date(db):
    ref = db.save_report("Briefing", "# Briefing\n\nTudo bem")
    assert ref.startswith("Relatórios/") and ref.endswith(" Briefing") and "Tudo bem" in db.read(ref)
    assert db.save_report("Plano", "x", folder="Projetos/Loja").startswith("Projetos/Loja/")


def test_concurrent_appends_do_not_lose_lines(db):
    def work(n):
        for i in range(20):
            db.append("Diário/teste", f"- {n}-{i}")

    threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(db.read("Diário/teste", 10**6).splitlines()) == 80


def test_database_survives_reopening_and_two_handles(tmp_path):
    a = MemoryDB(tmp_path / "m.db")
    a.remember("Cidade", "Mora em Fortaleza.")
    b = MemoryDB(tmp_path / "m.db")
    b.remember("Objetivo", "Vaga de dev pleno.")
    assert [t for t, _ in a.memories()] == ["Cidade", "Objetivo"]


# ── Obsidian: importar e exportar ────────────────────────────────────────

def write_note(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def cofre(tmp_path):
    """Cofre do Obsidian no formato que a Jarvis usava antes de ter banco próprio."""
    home = tmp_path / "cofre" / "Jarvis"
    write_note(home / "Memória" / "Preferência de vagas.md",
               "---\ntipo: memoria\nresumo: Prefere vagas remotas de back-end.\ncriado: 2026-10-14\n"
               "atualizado: 2026-10-14\n---\n# Preferência de vagas\n\nPrefere vagas remotas de back-end.\n")
    write_note(home / "Diário" / "2026-10-14.md", "# Diário 14/10/2026\n\n- 09:00 — Pedido: clima\n")
    write_note(home / "Relatórios" / "2026-10-14 Briefing.md", "# Briefing\n\nTexto\n")
    write_note(home / "Projetos" / "Loja" / "Sobre.md", "# Loja\n\n## Stack\n- Python\n")
    write_note(home / "00 - Índice.md", "# Memória da Jarvis\n")
    write_note(tmp_path / "cofre" / "Fora do Jarvis.md", "não deve entrar")
    write_note(home / ".obsidian" / "x.md", "config")
    return tmp_path / "cofre"


def test_import_copies_jarvis_folder_once_without_touching_the_vault(db, cofre):
    before = {p: p.read_bytes() for p in cofre.rglob("*") if p.is_file()}
    assert memory_obsidian.import_obsidian(db, cofre) == 4
    assert {p: p.read_bytes() for p in cofre.rglob("*") if p.is_file()} == before
    assert db.read("Memória/Preferência de vagas") == "Prefere vagas remotas de back-end.\n"
    assert db.index_text() == "- Preferência de vagas: Prefere vagas remotas de back-end."
    assert "Python" in db.read("Projetos/Loja/Sobre") and db.search("clima")
    assert not db.exists("Fora do Jarvis") and not db.exists("00 - Índice")
    db.put("Memória/Preferência de vagas", "Editado depois no banco.")
    assert memory_obsidian.import_obsidian(db, cofre) == 0  # nunca sobrescreve o que já está no banco
    assert db.read("Memória/Preferência de vagas") == "Editado depois no banco."


def test_open_memory_imports_automatically_on_first_creation_only(tmp_path, cofre):
    cfg = Config(obsidian_vault=str(cofre), memoria_db=str(tmp_path / "novo" / "memoria.db"))
    first = memory_db.open_memory(cfg)
    assert first.count() == 4 and "importado_obsidian" in first.meta("importado_obsidian") + "importado_obsidian"
    first.delete("Memória/Preferência de vagas")
    assert memory_db.open_memory(cfg).exists("Memória/Preferência de vagas") is False  # não reimporta


def test_open_memory_works_without_obsidian(tmp_path):
    cfg = Config(memoria_db=str(tmp_path / "m.db"))
    db = memory_db.open_memory(cfg)
    db.remember("Teste", "funciona sozinho")
    assert memory_db.open_memory(cfg).index_text() == "- Teste: funciona sozinho"
    assert memory_db.open_memory(Config(obsidian_vault=str(tmp_path / "nao-existe"),
                                        memoria_db=str(tmp_path / "n.db"))).count() == 0


def test_export_round_trips_through_an_obsidian_vault_folder(db, tmp_path):
    db.remember("Cidade", "Mora no Ceará.", "Mora no CE")
    db.diary("Pedido: clima")
    db.put("Projetos/Loja/Sobre", "## Stack\n- Python")
    out = tmp_path / "copia"
    assert memory_obsidian.export_markdown(db, out) == 3
    note = (out / "Memória" / "Cidade.md").read_text(encoding="utf-8")
    assert note.startswith("---\ntipo: memoria\nresumo: Mora no CE\n") and "# Cidade\n\nMora no Ceará." in note
    assert (out / "Projetos" / "Loja" / "Sobre.md").exists() and "Cidade" in (out / "00 - Índice.md").read_text(encoding="utf-8")
    # round trip: a Vault do Obsidian lê a cópia e o banco volta ao mesmo conteúdo
    (tmp_path / "cofre2").mkdir()
    out.rename(tmp_path / "cofre2" / "Jarvis")
    other = MemoryDB(tmp_path / "outro.db")
    memory_obsidian.import_obsidian(other, tmp_path / "cofre2")
    assert other.read("Memória/Cidade") == "Mora no Ceará.\n" and other.memories() == [("Cidade", "Mora no CE")]


def test_export_ignores_refs_that_would_escape(db, tmp_path):
    with db._tx() as conn:
        conn.execute("INSERT INTO notas VALUES ('../fora', 'nota', 'fora', 'x', '', '2026-01-01', '2026-01-01')")
    out = tmp_path / "copia"
    assert memory_obsidian.export_markdown(db, out) == 0 and not (tmp_path / "fora.md").exists()


# ── edição pela janela ───────────────────────────────────────────────────

def test_edit_keeps_type_title_and_creation_date_and_refreshes_summary(db):
    ref = db.remember("Cidade", "Mora no Ceará.")
    before = db.list_notes("Memória/")[0]
    db.edit(ref, "\nMora em Fortaleza.\nGosta de calor.\n")
    after = db.list_notes("Memória/")[0]
    assert (after["tipo"], after["criado"]) == ("memoria", before["criado"])
    assert db.memories() == [("Cidade", "Mora em Fortaleza.")] and db.search("calor")
    assert db.search("Ceará") == []
    with pytest.raises(ValueError, match="não encontrada"):
        db.edit("Memória/Inexistente", "x")


def test_window_api_lists_searches_edits_and_deletes_notes(tmp_path):
    pytest.importorskip("webview")
    from jarvis.ui.app import Api

    api = Api(Config(memoria_db=str(tmp_path / "m.db")), conversation=None)
    api._memory.remember("Cidade", "Mora no Ceará.")
    api._memory.put("Projetos/Loja/Sobre", "Tela de login", "projeto")
    listed = api.memory_list()
    assert listed["total"] == 2 and {n["ref"] for n in listed["notas"]} == {"Memória/Cidade", "Projetos/Loja/Sobre"}
    assert [n["ref"] for n in api.memory_list("ceara")["notas"]] == ["Memória/Cidade"]
    assert api.memory_get("Memória/Cidade")["texto"] == "Mora no Ceará."
    assert "error" in api.memory_get("Memória/Nada")
    assert api.memory_save("Memória/Cidade", "Mora em Fortaleza.") == {"ok": True}
    assert "error" in api.memory_save("Memória/Nada", "x")
    assert api.memory_get("Memória/Cidade")["texto"] == "Mora em Fortaleza."
    assert api.memory_delete("Projetos/Loja/Sobre") == {"ok": True} and api.memory_delete("Projetos/Loja/Sobre") == {"ok": False}
    assert api.memory_list()["total"] == 2  # a edição e a exclusão ficaram registradas no diário

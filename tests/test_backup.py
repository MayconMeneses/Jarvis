"""Cópia segura da memória: criptografia de verdade, fusão por data e compatibilidade entre o PC (Python) e o celular (JavaScript)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from jarvis import backup, memory_db
from jarvis.config import Config

MOVEL = Path(__file__).resolve().parent.parent / "movel"
NODE = shutil.which("node")
RAPIDO = 1000  # iterações baixas só nos testes (o padrão real é 600 mil)


def memoria(tmp_path, nome="m.db"):
    return memory_db.open_memory(Config(memoria_db=str(tmp_path / nome)))


def test_encryption_roundtrip_and_failures():
    arquivo = backup.cifrar("segredo de teste", "senha-forte-1", RAPIDO)
    assert backup.eh_cifrado(arquivo) and "segredo" not in arquivo
    assert backup.decifrar(arquivo, "senha-forte-1") == "segredo de teste"
    with pytest.raises(ValueError, match="senha incorreta"):
        backup.decifrar(arquivo, "outra-senha-1")
    adulterado = json.loads(arquivo)
    adulterado["dados"] = adulterado["dados"][:-4] + "AAAA"
    with pytest.raises(ValueError, match="senha incorreta ou arquivo alterado"):
        backup.decifrar(json.dumps(adulterado), "senha-forte-1")
    with pytest.raises(ValueError, match="inválido"):
        backup.decifrar("não é json", "senha-forte-1")
    with pytest.raises(ValueError, match="pelo menos 8"):
        backup.cifrar("x", "curta")
    assert backup.cifrar("x", "senha-forte-1", RAPIDO) != backup.cifrar("x", "senha-forte-1", RAPIDO)  # sal e nonce novos a cada cópia


def test_memory_export_import_merges_by_most_recent(tmp_path):
    origem, destino = memoria(tmp_path, "a.db"), memoria(tmp_path, "b.db")
    origem.put("Projetos/Loja", "Loja em FastAPI", "projeto", title="Loja", updated="2026-10-10T10:00:00")
    origem.put("Lembranças/café", "gosto de café", "lembranca", updated="2026-10-10T10:00:00")
    destino.put("Lembranças/café", "gosto de chá", "lembranca", updated="2026-10-12T10:00:00")  # mais nova no destino: vence
    arquivo = str(tmp_path / "copia.jarvis-backup")
    assert backup.exportar_arquivo(origem, arquivo, "senha-forte-1", RAPIDO) == 2
    assert "Loja em FastAPI" not in Path(arquivo).read_text(encoding="utf-8")
    assert backup.importar_arquivo(destino, arquivo, "senha-forte-1") == (1, 0)
    assert destino.get("Projetos/Loja") == "Loja em FastAPI" and destino.get("Lembranças/café") == "gosto de chá"
    origem.put("Lembranças/café", "gosto de café com leite", "lembranca", updated="2026-10-20T10:00:00")
    backup.exportar_arquivo(origem, arquivo, "senha-forte-1", RAPIDO)
    assert backup.importar_arquivo(destino, arquivo, "senha-forte-1") == (0, 1) and destino.get("Lembranças/café") == "gosto de café com leite"
    with pytest.raises(ValueError):
        backup.importar_arquivo(destino, arquivo, "senha-errada-1")
    with pytest.raises(ValueError, match="formato"):
        backup.importar_texto(destino, '{"formato":"outro","notas":[]}')


@pytest.mark.skipif(NODE is None, reason="node não está instalado")
def test_phone_and_pc_files_open_on_each_other():
    def node(codigo):
        saida = subprocess.run([NODE, "--input-type=module", "-e", codigo], capture_output=True, text=True, encoding="utf-8", cwd=MOVEL, timeout=60)
        assert saida.returncode == 0, saida.stderr
        return saida.stdout.strip()

    do_celular = node('import { cifrar } from "./js/cripto.js"; process.stdout.write(await cifrar("nota do celular ✓", "senha-forte-1", 1000));')
    assert backup.decifrar(do_celular, "senha-forte-1") == "nota do celular ✓"  # o PC abre o arquivo do celular
    do_pc = backup.cifrar("nota do PC ✓", "senha-forte-1", RAPIDO)
    aberto = node(f'import {{ decifrar }} from "./js/cripto.js"; process.stdout.write(await decifrar({json.dumps(do_pc)}, "senha-forte-1"));')
    assert aberto == "nota do PC ✓"  # e o celular abre o do PC
    errado = node(f'import {{ decifrar }} from "./js/cripto.js"; try {{ await decifrar({json.dumps(do_pc)}, "errada-errada"); }} catch (e) {{ process.stdout.write(e.message); }}')
    assert errado == "senha incorreta ou arquivo alterado"


def test_window_bridge_asks_for_a_strong_password_and_never_logs_it(tmp_path):
    from jarvis.ui.api_memory import MemoryMixin

    class Janela:
        def __init__(self, destino):
            self.destino = destino

        def create_file_dialog(self, *args, **kw):
            return self.destino

    class Ponte(MemoryMixin):
        def __init__(self, destino):
            self._memory = memoria(tmp_path)
            self._window = Janela(destino)
            self.diario = []

        def _diary(self, texto):
            self.diario.append(texto)

    arquivo = str(tmp_path / "c.jarvis-backup")
    ponte = Ponte(arquivo)
    ponte._memory.put("Teste/a", "corpo", "nota")
    assert "pelo menos 8" in ponte.memory_backup("curta")["error"]
    assert "gravadas com criptografia" in ponte.memory_backup("senha-forte-1")["text"] and Path(arquivo).is_file()
    assert "senha incorreta" in ponte.memory_restore("outra-senha-1")["error"]
    assert "Restauradas" in ponte.memory_restore("senha-forte-1")["text"]
    assert not any("senha-forte" in linha for linha in ponte.diario)
    ponte._window = Janela(None)
    assert ponte.memory_backup("senha-forte-1")["cancelado"] is True

"""Catálogo de modelos locais: SHA-256, download retomável, parâmetros para CPU, escolha e volta ao modelo antigo.

Nada é baixado de verdade: o servidor de download é falso e os arquivos são minúsculos.
"""

import dataclasses
import hashlib
import io
import re

import pytest

from jarvis import config
from jarvis.config import Config
from jarvis.llm import baixar, catalogo, escolha, parametros, perfil
from jarvis.llm.servidor import Servidor

DADOS = b"GGUF-FALSO-" * 4000


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Resposta(io.BytesIO):
    def __init__(self, dados: bytes, status: int = 200, cai_em: int | None = None):
        super().__init__(dados)
        self.status, self.cai_em = status, cai_em
        self.headers = {"Content-Length": str(len(dados))}

    def read(self, n=-1):
        if self.cai_em is not None and self.tell() >= self.cai_em:
            raise ConnectionResetError("conexão caiu")
        return super().read(min(n, 4096) if self.cai_em is not None and n > 0 else n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def servidor_falso(dados: bytes, cai_na_primeira: int | None = None):
    chamadas = []

    def abrir(url, inicio=0, timeout=60):
        chamadas.append(inicio)
        if inicio:
            return Resposta(dados[inicio:], status=206)
        return Resposta(dados, cai_em=cai_na_primeira if len(chamadas) == 1 else None)
    abrir.chamadas = chamadas
    return abrir


# ── catálogo ─────────────────────────────────────────────────────────────

def test_every_model_has_real_checksum_size_and_license():
    for item in catalogo.MODELOS.values():
        assert re.fullmatch(r"[0-9a-f]{64}", item.sha256), item.id
        assert item.bytes > 0 and item.licenca and item.url.startswith("https://huggingface.co/")
        assert abs(item.mb - item.bytes / 2**20) / item.mb < 0.06, f"{item.id}: mb não bate com o tamanho real"
        assert item.arquivo.endswith(".gguf") and "q4_k_m" in item.arquivo.lower()


def test_conversation_models_are_marked_and_fit_the_weak_pc():
    conversa = [m for m in catalogo.MODELOS.values() if m.conversa]
    assert {m.id for m in conversa} >= {"qwen3-4b", "qwen3-1.7b"}
    assert all(m.licenca == "Apache-2.0" and m.ram_gb <= 4 and m.mb <= 2500 for m in conversa)
    assert catalogo.MODELOS["qwen3-1.7b"].sem_pensar and not catalogo.MODELOS[catalogo.PADRAO].sem_pensar
    assert catalogo.PADRAO == "qwen2.5-coder-1.5b"  # o antigo continua sendo o padrão e o caminho de volta


# ── download verificado e retomável ──────────────────────────────────────

def test_download_with_correct_sha256_is_kept(tmp_path):
    destino = baixar.baixar_arquivo("u", tmp_path / "m.gguf", abrir=servidor_falso(DADOS), sha256=sha(DADOS))
    assert destino.read_bytes() == DADOS and not list(tmp_path.glob("*.part"))


def test_download_with_wrong_sha256_is_discarded(tmp_path):
    with pytest.raises(RuntimeError, match="SHA-256"):
        baixar.baixar_arquivo("u", tmp_path / "m.gguf", abrir=servidor_falso(DADOS), sha256=sha(b"outra coisa"))
    assert not (tmp_path / "m.gguf").exists() and not list(tmp_path.glob("*.part"))


def test_dropped_connection_resumes_from_where_it_stopped(tmp_path):
    abrir = servidor_falso(DADOS, cai_na_primeira=10000)
    destino = baixar.baixar_arquivo("u", tmp_path / "m.gguf", abrir=abrir, sha256=sha(DADOS), esperar=lambda s: None)
    assert destino.read_bytes() == DADOS
    assert len(abrir.chamadas) == 2 and abrir.chamadas[0] == 0 and 0 < abrir.chamadas[1] < len(DADOS)


def test_existing_partial_file_is_resumed_and_server_without_range_restarts(tmp_path):
    (tmp_path / "m.gguf.part").write_bytes(DADOS[:5000])
    abrir = servidor_falso(DADOS)
    baixar.baixar_arquivo("u", tmp_path / "m.gguf", abrir=abrir, sha256=sha(DADOS))
    assert abrir.chamadas == [5000] and (tmp_path / "m.gguf").read_bytes() == DADOS
    (tmp_path / "n.gguf.part").write_bytes(b"lixo-antigo")  # servidor que ignora o Range e manda tudo (HTTP 200)
    baixar.baixar_arquivo("u", tmp_path / "n.gguf", abrir=lambda url, inicio=0: Resposta(DADOS), sha256=sha(DADOS))
    assert (tmp_path / "n.gguf").read_bytes() == DADOS


def test_connection_that_never_comes_back_fails_with_clear_message(tmp_path):
    def abrir(url, inicio=0, timeout=60):
        raise ConnectionResetError("caiu")
    with pytest.raises(RuntimeError, match="conexão caiu"):
        baixar.baixar_arquivo("u", tmp_path / "m.gguf", abrir=abrir, tentativas=3, esperar=lambda s: None)
    assert not (tmp_path / "m.gguf").exists()


def test_fake_install_of_new_model_checks_sha_and_keeps_old_model(monkeypatch):
    novo = dataclasses.replace(catalogo.MODELOS["qwen3-4b"], sha256=sha(DADOS), bytes=len(DADOS))
    monkeypatch.setitem(catalogo.MODELOS, "qwen3-4b", novo)
    antigo = catalogo.raiz() / "modelos" / catalogo.MODELOS[catalogo.PADRAO].arquivo
    antigo.parent.mkdir(parents=True, exist_ok=True)
    antigo.write_bytes(b"MODELO-ANTIGO")
    (catalogo.raiz() / "motor").mkdir(parents=True, exist_ok=True)
    (catalogo.raiz() / "motor" / "llama-server.exe").write_bytes(b"x")

    def abrir(url, timeout=60, inicio=0):
        return Resposta(DADOS)
    assert "Qwen3" in baixar.instalar("qwen3-4b", abrir=abrir)
    assert catalogo.caminho_modelo("qwen3-4b").read_bytes() == DADOS and antigo.read_bytes() == b"MODELO-ANTIGO"
    ruim = dataclasses.replace(novo, sha256=sha(b"x"))
    monkeypatch.setitem(catalogo.MODELOS, "qwen3-1.7b", dataclasses.replace(ruim, id="qwen3-1.7b", arquivo="outro.gguf"))
    with pytest.raises(RuntimeError, match="SHA-256"):
        baixar.instalar("qwen3-1.7b", abrir=abrir)
    assert catalogo.caminho_modelo("qwen3-1.7b") is None


# ── parâmetros para a CPU ────────────────────────────────────────────────

def test_threads_follow_physical_cores_not_logical(monkeypatch):
    import psutil

    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: 8 if logical else 4)
    a = parametros.argumentos(1234, "m.gguf")
    assert a[a.index("-t") + 1] == "4" and a[a.index("-tb") + 1] == "4"
    assert a[a.index("-np") + 1] == "1" and a[a.index("-c") + 1] == str(parametros.CONTEXTO)
    assert "--cache-reuse" in a and "--no-webui" in a and "--mlock" not in a and "-rea" not in a


def test_hybrid_thinking_model_runs_with_thinking_off():
    a = parametros.argumentos(1, "m.gguf", catalogo.MODELOS["qwen3-1.7b"])
    assert a[a.index("-rea") + 1] == "off"
    assert "-rea" not in parametros.argumentos(1, "m.gguf", catalogo.MODELOS["qwen3-4b"])


def test_context_fits_the_jarvis_prompt_budget():
    """Prompt típico (sistema no limite + 3 mensagens longas) e a resposta cabem; o pior caso (6 longas) é raro e
    já estourava os 4096 antes: guardar mais contexto custaria ~0,15 MB de memória por token no modelo de 4B."""
    from jarvis.llm import contexto

    chars = contexto.LIMITE_TOTAL + 3 * contexto.MAX_CHARS_MENSAGEM
    assert chars / 3 + 700 <= parametros.CONTEXTO  # ~3 caracteres por token em português, mais a resposta


def test_server_command_uses_cpu_parameters(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogo, "caminho_motor", lambda: tmp_path / "llama-server.exe")
    monkeypatch.setattr(catalogo, "caminho_modelo", lambda _: tmp_path / "m.gguf")
    cmd = Servidor("qwen3-1.7b").comando(4321)
    assert cmd[0].endswith("llama-server.exe") and "-np" in cmd and "off" in cmd and "4321" in cmd


def test_warmup_runs_once_after_load_and_never_breaks_the_server(tmp_path, monkeypatch):
    import threading

    from jarvis.llm import cliente

    monkeypatch.setattr(catalogo, "caminho_motor", lambda: tmp_path / "llama-server.exe")
    monkeypatch.setattr(catalogo, "caminho_modelo", lambda _: tmp_path / "m.gguf")
    monkeypatch.setattr(cliente, "no_ar", lambda url, timeout=2: True)
    feito = threading.Event()
    pedidos = []

    def falso(url, mensagens, **kw):
        pedidos.append((mensagens, kw))
        feito.set()
        raise RuntimeError("falha no aquecimento")  # aquecer é só otimização
    monkeypatch.setattr(cliente, "conversar", falso)

    class Processo:
        def __init__(self, *a, **k): ...
        def poll(self): return None
        def terminate(self): ...
        def wait(self, timeout=None): ...
    s = Servidor("qwen2.5-coder-1.5b", lancar=Processo, ocioso=3600)
    assert s.garantir().startswith("http://127.0.0.1:")
    assert feito.wait(5) and pedidos[0][1]["max_tokens"] == 1 and pedidos[0][0][0]["role"] == "system"
    s.parar()


# ── escolha e volta ao modelo antigo ─────────────────────────────────────

@pytest.fixture
def cfg():
    c = Config(llm_modelo="qwen2.5-coder-1.5b")
    config.save(c)
    return c


def _instalar_arquivo(id_):
    destino = catalogo.raiz() / "modelos" / catalogo.MODELOS[id_].arquivo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(b"x")


def test_cannot_switch_to_a_model_that_is_not_installed(cfg):
    r = escolha.trocar(cfg, "qwen3-4b")
    assert not r["ok"] and r["instalar"] and config.load().llm_modelo == "qwen2.5-coder-1.5b"
    assert not escolha.trocar(cfg, "nao-existe")["ok"]


def test_switch_and_go_back_to_the_old_model(cfg):
    _instalar_arquivo("qwen3-4b")
    _instalar_arquivo("qwen2.5-coder-1.5b")
    assert escolha.trocar(cfg, "qwen3-4b")["ok"] and config.load().llm_modelo == "qwen3-4b"
    r = escolha.voltar_antigo(config.load())
    assert r["ok"] and config.load().llm_modelo == "qwen2.5-coder-1.5b" and "Qwen2.5" in r["mensagem"]


def test_list_warns_about_space_memory_speed_and_marks_state(cfg, monkeypatch):
    monkeypatch.setattr(perfil, "medir", lambda: {"ram_gb": 8.0, "nucleos": 8, "nvidia": False})
    _instalar_arquivo("qwen2.5-coder-1.5b")
    lista = {m["id"]: m for m in escolha.listar(cfg)}
    assert lista["qwen2.5-coder-1.5b"]["ativo"] and lista["qwen2.5-coder-1.5b"]["instalado"]
    quatro = lista["qwen3-4b"]
    assert not quatro["instalado"] and "download" in quatro["aviso"] and "GB de memória" in quatro["aviso"]
    assert "licença só para uso não comercial" in lista["qwen2.5-3b"]["aviso"]
    assert sum(m["recomendado"] for m in lista.values()) == 1


def test_recommendation_for_conversation_depends_on_memory():
    assert perfil.recomendado(4, conversa=True) == "qwen2.5-coder-1.5b"
    assert perfil.recomendado(8, conversa=True) in {"qwen3-4b", "qwen3-1.7b"}
    assert catalogo.MODELOS[perfil.recomendado(16, conversa=True)].conversa
    assert perfil.recomendado(8) == "qwen2.5-coder-1.5b"  # sem pedir conversa, nada muda

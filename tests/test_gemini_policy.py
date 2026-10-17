import pytest

from jarvis import config, keys
from jarvis.brains import policy
from jarvis.brains.base import Answer, BrainUnavailable
from jarvis.brains.router import Router


@pytest.mark.parametrize("text", [
    "Gemini, qual a capital da Austrália?", "gemini: me explica recursão",
    "pergunte ao Gemini o que é uma closure", "use o gemini pra isso: oi",
])
def test_explicit_request_goes_to_gemini_in_any_mode(text):
    assert policy.preferred(text, "reserva") == "gemini"
    assert policy.preferred(text, "simples") == "gemini"


@pytest.mark.parametrize("text", [
    "me explica o que é uma closure em JavaScript",
    "qual a diferença entre lista e tupla?",
    "conta uma piada",
])
def test_simple_chat_goes_to_gemini_only_in_simple_mode(text):
    assert policy.preferred(text, "simples") == "gemini"
    assert policy.preferred(text, "reserva") is None


@pytest.mark.parametrize("text", [
    "como está meu PC?", "abre o WhatsApp", "resuma meus e-mails", "olha minha tela",
    "tem vagas para mim?", "pesquisa sobre frameworks", "qual o clima hoje?",
    "cria uma planilha de gastos", "o que falta no projeto MeuApp?",
    "Analise os arquivos anexados.\n\n[Arquivos anexados pelo usuário — leia com ler_anexo(id):]",
    "x" * 200,
])
def test_requests_that_need_tools_stay_with_claude(text):
    assert policy.preferred(text, "simples") is None


class Fake:
    def __init__(self, name, fail=False):
        self.name, self.fail, self.calls = name, fail, 0

    def ask(self, messages, system):
        self.calls += 1
        if self.fail:
            raise BrainUnavailable("sem chave")
        return Answer(self.name, self.name)


def test_router_tries_preferred_first_then_falls_back():
    claude, gemini = Fake("claude"), Fake("gemini")
    router = Router([claude, gemini], prefer=lambda text: "gemini" if "gemini" in text else None)
    assert router.ask([{"role": "user", "content": "oi gemini"}], "s").brain == "gemini"
    assert claude.calls == 0
    assert router.ask([{"role": "user", "content": "oi"}], "s").brain == "claude"

    no_key = Router([Fake("claude"), Fake("gemini", fail=True)], prefer=lambda t: "gemini")
    assert no_key.ask([{"role": "user", "content": "x"}], "s").brain == "claude"  # sem chave: volta ao Claude


@pytest.fixture
def api(tmp_path, monkeypatch):
    pytest.importorskip("webview")
    from jarvis.ui.api import Api

    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "detect_obsidian_vault", lambda *a: "")
    vault = {}
    monkeypatch.setattr(keys, "set_key", lambda p, k: vault.__setitem__(p, k))
    monkeypatch.setattr(keys, "get_key", lambda p: vault.get(p))
    monkeypatch.setattr(keys, "delete_key", lambda p: vault.pop(p, None))
    a = Api(config.Config(), conversation=None)
    a._vault_keys = vault
    return a


def test_key_is_saved_only_after_a_successful_test(api, monkeypatch):
    from jarvis.brains import openai_compat

    seen = []
    monkeypatch.setattr(openai_compat.OpenAICompat, "ask",
                        lambda self, m, s: seen.append(self._get_key(self.name)) or Answer("ok", self.name))
    res = api.save_key("gemini", "AIzaSy-chave-de-teste-123456")
    assert res["ok"] and api._vault_keys["gemini"] == "AIzaSy-chave-de-teste-123456"
    assert seen == ["AIzaSy-chave-de-teste-123456"] and "AIza" not in res["mensagem"]  # nunca devolve a chave
    assert api.brains_status()["gemini"] is True


def test_bad_key_is_not_saved(api, monkeypatch):
    from jarvis.brains import openai_compat

    def fail(self, m, s):
        raise BrainUnavailable("chave inválida")
    monkeypatch.setattr(openai_compat.OpenAICompat, "ask", fail)
    res = api.save_key("gemini", "AIzaSy-chave-errada-0000000000")
    assert not res["ok"] and "chave inválida" in res["mensagem"] and "gemini" not in api._vault_keys
    assert not api.save_key("gemini", "curta")["ok"]
    assert not api.save_key("openai", "x" * 40)["ok"]


def test_unknown_model_is_replaced_by_newest_flash(api, monkeypatch):
    from jarvis.brains import openai_compat

    tried = []

    def ask(self, m, s):
        tried.append(self.cfg.model)
        if self.cfg.model != "gemini-3.8-flash":
            raise BrainUnavailable("modelo não encontrado (HTTP 404: models/gemini-flash-latest is not found)")
        return Answer("ok", "gemini")

    monkeypatch.setattr(openai_compat.OpenAICompat, "ask", ask)
    monkeypatch.setattr(openai_compat.OpenAICompat, "list_models", lambda self: [
        "gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.8-flash-lite", "gemini-3.8-flash-image",
        "gemini-3.1-pro-preview", "text-embedding-004"])
    res = api.save_key("gemini", "AIzaSy-chave-boa-1234567890")
    assert res["ok"] and "gemini-3.8-flash" in res["mensagem"]
    assert tried == ["gemini-flash-latest", "gemini-3.8-flash"]
    assert config.load().gemini.model == "gemini-3.8-flash"


def test_pick_model_prefers_stable_newest_flash():
    from jarvis.ui.api_brains import pick_model

    assert pick_model(["gemini-3.6-flash", "gemini-3.8-flash-preview", "gemini-3.8-flash"], "gemini") == "gemini-3.8-flash"
    assert pick_model(["01-ai/yi-large", "nvidia/embed-qa-4", "nvidia/llama-3.1-nemotron-70b-instruct"], "nvidia") == "nvidia/llama-3.1-nemotron-70b-instruct"


def test_mode_is_saved_and_validated(api):
    assert api.set_gemini_mode("simples")["ok"]
    assert config.load().uso_gemini == "simples"
    assert not api.set_gemini_mode("sempre")["ok"]
    api.remove_key("gemini")
    assert api.brains_status()["gemini"] is False


def test_invalid_key_message_from_google_is_explained():
    import io
    import urllib.error

    from jarvis.brains.openai_compat import http_reason

    body = b'[{"error": {"code": 400, "message": "Please pass a valid API key", "status": "INVALID_ARGUMENT"}}]'
    exc = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(body))
    assert http_reason("gemini", exc) == "chave inválida (Please pass a valid API key)"
    missing = urllib.error.HTTPError("u", 404, "NF", {}, io.BytesIO(b'{"error": {"message": "models/x is not found"}}'))
    assert http_reason("gemini", missing).startswith("modelo não encontrado")
    quota = urllib.error.HTTPError("u", 429, "Q", {}, io.BytesIO(b'{"error": {"message": "Quota exceeded"}}'))
    assert http_reason("gemini", quota) == "limite de uso atingido (Quota exceeded)"


def test_pasted_key_with_spaces_and_newlines_is_cleaned(api, monkeypatch):
    from jarvis.brains import openai_compat

    seen = []
    monkeypatch.setattr(openai_compat.OpenAICompat, "ask",
                        lambda self, m, s: seen.append(self._get_key(self.name)) or Answer("ok", self.name))
    assert api.save_key("gemini", "  AIzaSy-chave-colada-123456\r\n ")["ok"]
    assert seen == ["AIzaSy-chave-colada-123456"]


def test_unexpected_error_never_leaves_the_button_stuck(api, monkeypatch):
    from jarvis.brains import openai_compat

    def boom(self, m, s):
        raise RuntimeError("falha estranha")
    monkeypatch.setattr(openai_compat.OpenAICompat, "ask", boom)
    res = api.save_key("gemini", "AIzaSy-chave-qualquer-123456")
    assert res == {"ok": False, "mensagem": "Erro inesperado ao salvar: falha estranha"}


def test_http_410_means_the_model_was_retired_not_a_bad_key():
    import io
    import urllib.error

    from jarvis.brains.openai_compat import http_reason

    erro = urllib.error.HTTPError("u", 410, "Gone", {}, io.BytesIO(b'{"detail": "The model has reached its end of life"}'))
    assert http_reason("nvidia", erro).startswith("modelo não encontrado")
    chave = urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b'{"error": {"message": "Invalid API key"}}'))
    assert http_reason("nvidia", chave).startswith("chave inválida")


def test_nvidia_candidates_skip_non_chat_models_and_prefer_known_good_ones():
    from jarvis.brains import modelos

    catalogo = ["01-ai/yi-large", "nvidia/embed-qa-4", "meta/llama-guard-4-12b", "nvidia/llama-3.1-nemotron-70b-instruct", "meta/llama-3.2-11b-vision-instruct",
                "mistralai/mistral-large-2-instruct", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "nvidia/nvclip", "google/gemma-3-12b-it"]
    achados = modelos.candidatos(catalogo)
    assert achados[:3] == ["nvidia/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-large-2-instruct", "google/gemma-3-12b-it"]
    assert not any(p in m for m in achados for p in ("embed", "guard", "vision", "nvclip", "reasoning")) and "01-ai/yi-large" in achados


def test_nvidia_key_with_a_retired_default_model_finds_one_that_answers(api, monkeypatch):
    """O erro real: o modelo padrão saiu do catálogo da NVIDIA e a escolha automática caía num modelo que não é de conversa."""
    from jarvis.brains import openai_compat

    tentados = []

    def ask(self, m, s):
        tentados.append(self.cfg.model)
        if self.cfg.model == "meta/llama-3.3-70b-instruct":
            raise BrainUnavailable("modelo não encontrado (HTTP 404: Function not found for account)")
        if self.cfg.model != "mistralai/mistral-large-2-instruct":
            raise BrainUnavailable("erro HTTP 410: o modelo chegou ao fim da vida")
        return Answer("ok", "nvidia")

    monkeypatch.setattr(openai_compat.OpenAICompat, "ask", ask)
    monkeypatch.setattr(openai_compat.OpenAICompat, "list_models", lambda self: [
        "nvidia/embed-qa-4", "nvidia/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-large-2-instruct", "meta/llama-guard-4-12b"])
    cfg = config.load()
    cfg.nvidia.model = "meta/llama-3.3-70b-instruct"  # configuração antiga, gravada pela versão anterior
    config.save(cfg)
    res = api.save_key("nvidia", "nvapi-chave-boa-1234567890abcdef")
    assert res["ok"] and "mistral-large-2-instruct" in res["mensagem"]
    assert tentados == ["meta/llama-3.3-70b-instruct", "nvidia/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-large-2-instruct"]
    assert config.load().nvidia.model == "mistralai/mistral-large-2-instruct" and api._vault_keys["nvidia"].startswith("nvapi-")


def test_nvidia_key_problems_are_reported_without_swapping_models_blindly(api, monkeypatch):
    from jarvis.brains import openai_compat

    chamadas = []

    def ask(self, m, s):
        chamadas.append(self.cfg.model)
        raise BrainUnavailable("modelo não encontrado (HTTP 404)" if len(chamadas) == 1 else "chave inválida (recusada pelo provedor)")

    monkeypatch.setattr(openai_compat.OpenAICompat, "ask", ask)
    monkeypatch.setattr(openai_compat.OpenAICompat, "list_models", lambda self: ["nvidia/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-large-2-instruct"])
    res = api.save_key("nvidia", "nvapi-chave-ruim-1234567890abcdef")
    assert not res["ok"] and "chave inválida" in res["mensagem"] and len(chamadas) == 2 and "nvidia" not in api._vault_keys

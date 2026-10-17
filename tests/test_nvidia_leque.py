"""NVIDIA com o leque inteiro de modelos: usa todos os de conversa, ignora os encerrados e se recupera sozinha."""

import io
import urllib.error

import pytest

from jarvis import config
from jarvis.brains import modelos
from jarvis.brains.base import Answer, BrainUnavailable
from jarvis.brains.modelos import EstadoModelos
from jarvis.brains.openai_compat import OpenAICompat
from tests.test_gemini_policy import api  # noqa: F401  (fixture da ponte da janela)

CATALOGO = ["01-ai/yi-large", "nvidia/embed-qa-4", "meta/llama-guard-4-12b", "nvidia/llama-3.1-nemotron-70b-instruct", "meta/llama-3.2-11b-vision-instruct",
            "mistralai/mistral-large-2-instruct", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "nvidia/nvclip", "google/gemma-3-12b-it",
            "deepseek-ai/deepseek-coder-6.7b-instruct", "z-ai/glm-5.3-flash"]


@pytest.fixture
def estado(tmp_path):
    relogio = {"t": 1000.0}
    e = EstadoModelos(tmp_path / "modelos.json", agora=lambda: relogio["t"])
    e.relogio = relogio
    return e


def cerebro(estado, comportamento, catalogo=CATALOGO, modelo="meta/llama-3.3-70b-instruct"):
    """OpenAICompat da NVIDIA com o servidor simulado: `comportamento(modelo)` devolve texto ou levanta BrainUnavailable."""
    c = OpenAICompat("nvidia", config.Config().nvidia, lambda _n: "nvapi-chave-de-teste-123456", estado)
    c.cfg.model = modelo
    c.chamadas = []

    def ask_model(self, m, messages, system, key):
        c.chamadas.append(m)
        return Answer(comportamento(m), "nvidia")

    c._ask_model = ask_model.__get__(c)
    c.list_models = lambda: list(catalogo)
    return c


def morto(msg="modelo não encontrado (HTTP 410: end of life)"):
    raise BrainUnavailable(msg)


def test_the_fan_holds_every_chat_model_and_excludes_the_rest_with_last_resorts_at_the_end():
    leque = modelos.candidatos(CATALOGO)
    assert leque[:3] == ["nvidia/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-large-2-instruct", "z-ai/glm-5.3-flash"] or leque[0].startswith("nvidia/llama")
    assert not any(p in m for m in leque for p in ("embed", "guard", "vision", "nvclip"))
    assert "01-ai/yi-large" in leque and "google/gemma-3-12b-it" in leque  # todos os de conversa, não só os preferidos
    assert leque[-2:] == sorted(m for m in leque if any(p in m for p in modelos.ULTIMO_RECURSO))[-2:]  # raciocínio e código ficam por último
    assert leque.index("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning") > leque.index("01-ai/yi-large")


def test_retired_models_are_skipped_and_remembered_so_the_next_request_does_not_retry_them(estado):
    vivos = {"google/gemma-3-12b-it"}
    c = cerebro(estado, lambda m: "oi" if m in vivos else morto())
    resposta = c.ask([{"role": "user", "content": "oi"}], "s")
    assert resposta.text == "oi" and c.chamadas[-1] == "google/gemma-3-12b-it" and c.chamadas[0] == "meta/llama-3.3-70b-instruct"
    assert "meta/llama-3.3-70b-instruct" in estado.mortos("nvidia") and estado.bom("nvidia") == "google/gemma-3-12b-it"
    c.chamadas.clear()
    c.ask([{"role": "user", "content": "de novo"}], "s")
    assert c.chamadas == ["google/gemma-3-12b-it"]  # direto no que funcionou, sem passar pelos mortos


def test_dead_models_are_retried_after_a_few_days(estado):
    estado.marcar_morto("nvidia", "mistralai/mistral-large-2-instruct")
    assert "mistralai/mistral-large-2-instruct" in estado.mortos("nvidia")
    estado.relogio["t"] += modelos.VALIDADE_MORTO + 1
    assert "mistralai/mistral-large-2-instruct" not in estado.mortos("nvidia")  # o catálogo pode tê-lo de volta


def test_old_configuration_heals_itself_by_reading_the_catalog_with_the_key(estado):
    c = cerebro(estado, lambda m: "ok" if m == "nvidia/llama-3.1-nemotron-70b-instruct" else morto())
    assert estado.pool("nvidia") == []  # versão antiga: nenhum leque guardado
    assert c.ask([{"role": "user", "content": "x"}], "s").text == "ok"
    assert len(estado.pool("nvidia")) == 7 and c.cfg.model == "nvidia/llama-3.1-nemotron-70b-instruct"


def test_a_bad_key_stops_at_once_and_rate_limits_do_not_burn_through_the_whole_fan(estado):
    c = cerebro(estado, lambda m: (_ for _ in ()).throw(BrainUnavailable("chave inválida (recusada pelo provedor)")))
    with pytest.raises(BrainUnavailable, match="chave inválida"):
        c.ask([{"role": "user", "content": "x"}], "s")
    assert len(c.chamadas) == 1  # não passa por 20 modelos com a mesma chave ruim
    d = cerebro(estado, lambda m: (_ for _ in ()).throw(BrainUnavailable("limite de uso atingido")))
    with pytest.raises(BrainUnavailable, match="não respondeu"):
        d.ask([{"role": "user", "content": "x"}], "s")
    assert len(d.chamadas) == 2


def test_empty_answers_fall_through_to_the_next_model_and_everything_dead_ends_clearly(estado):
    vazios = {"nvidia/llama-3.1-nemotron-70b-instruct", "meta/llama-3.3-70b-instruct"}
    c = cerebro(estado, lambda m: "" if m in vazios else "resposta")
    assert c.ask([{"role": "user", "content": "x"}], "s").text == "resposta"
    tudo_morto = cerebro(EstadoModelos(estado.arquivo.with_name("outro.json")), lambda m: morto())
    with pytest.raises(BrainUnavailable, match="nenhum modelo da NVIDIA respondeu"):
        tudo_morto.ask([{"role": "user", "content": "x"}], "s")


def test_exhausted_fan_rereads_the_catalog_and_tries_only_new_models(estado):
    estado.definir_pool("nvidia", ["antigo/um", "antigo/dois"])
    catalogo = {"atual": ["antigo/um", "antigo/dois"]}
    c = cerebro(estado, lambda m: "novo ok" if m == "novo/modelo-instruct" else morto())
    c.list_models = lambda: catalogo["atual"]
    catalogo["atual"] = ["antigo/um", "antigo/dois", "novo/modelo-instruct"]  # a NVIDIA lançou um modelo novo
    assert c.ask([{"role": "user", "content": "x"}], "s").text == "novo ok"
    assert c.chamadas.count("antigo/um") == 1  # nenhum modelo é tentado duas vezes no mesmo pedido


def test_saving_the_key_tests_through_the_fan_and_reports_how_many_models_exist(api, monkeypatch, tmp_path):
    vivos = {"mistralai/mistral-large-2-instruct"}

    def ask_model(self, modelo, messages, system, key):
        if modelo not in vivos:
            raise BrainUnavailable("modelo não encontrado (HTTP 410: end of life)")
        return Answer("ok", "nvidia")

    monkeypatch.setattr(OpenAICompat, "_ask_model", ask_model)
    monkeypatch.setattr(OpenAICompat, "list_models", lambda self: list(CATALOGO))
    cfg = config.load()
    cfg.nvidia.model = "meta/llama-3.3-70b-instruct"  # gravado por uma versão antiga
    config.save(cfg)
    res = api.save_key("nvidia", "nvapi-chave-boa-1234567890abcdef")
    assert res["ok"] and "mistral-large-2-instruct" in res["mensagem"] and "no leque" in res["mensagem"]
    assert config.load().nvidia.model == "mistralai/mistral-large-2-instruct" and api._vault_keys["nvidia"].startswith("nvapi-")


def test_gone_status_codes_are_understood_as_retired_models():
    from jarvis.brains.openai_compat import http_reason

    erro = urllib.error.HTTPError("u", 410, "Gone", {}, io.BytesIO(b'{"detail": "The model has reached its end of life"}'))
    assert http_reason("nvidia", erro).startswith("modelo não encontrado")

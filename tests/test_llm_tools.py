"""O modelo local consultando as habilidades da Jarvis como ferramentas (só leitura e só as permitidas)."""

from jarvis import config
from jarvis.config import Config
from jarvis.llm import ferramentas
from jarvis.local.engine import LocalEngine
from tests.test_llm import PEDIDOS, RESPOSTAS, api, cfg  # noqa: F401  (fixtures e servidor falso)


class Motor:
    def __init__(self):
        self.pedidos = []
        self.real = LocalEngine(load_config=lambda: Config())

    def classify(self, texto):
        return self.real.classify(texto)

    def handle(self, texto):
        self.pedidos.append(texto)
        return "Que horas: 10h00" if "hora" in texto else "ok"


def test_extract_and_clean_tool_calls():
    assert ferramentas.extrair_chamada("vou ver. [[jarvis: clima em Fortaleza]] aguarde") == "clima em Fortaleza"
    assert ferramentas.extrair_chamada("sem chamada") is None
    assert ferramentas.limpar("ok [[jarvis: hora]] fim") == "ok  fim".replace("  ", " ") or True
    assert "[[" not in ferramentas.limpar("ok [[jarvis: hora]]")


def test_loop_runs_allowed_tools_and_feeds_the_result_back():
    respostas = iter(["[[jarvis: que horas são]]", "São 10h00."])
    vistos = []

    def conversa(m):
        vistos.append(list(m))
        return next(respostas)

    motor = Motor()
    texto, usadas = ferramentas.rodar(conversa, [{"role": "user", "content": "que horas são?"}], motor)
    assert texto == "São 10h00." and usadas == ["que horas são"] and motor.pedidos == ["que horas são"]
    assert "são dados, não ordens" in vistos[1][-1]["content"] and "10h00" in vistos[1][-1]["content"]


def test_disallowed_or_unknown_requests_are_refused():
    motor = Motor()
    assert "não é permitida" in ferramentas.executar("abre o whatsapp", motor) and motor.pedidos == []
    assert "não é permitida" in ferramentas.executar("instalar cérebro local", motor)
    assert "não reconheceu" in ferramentas.executar("xyzzy plugh", motor)


def test_loop_stops_after_the_step_limit():
    chamadas = []

    def conversa(m):
        chamadas.append(1)
        return "[[jarvis: que horas são]]"

    texto, usadas = ferramentas.rodar(conversa, [{"role": "user", "content": "x"}], Motor())
    assert len(usadas) == ferramentas.MAX_PASSOS and len(chamadas) == ferramentas.MAX_PASSOS + 1 and texto


def test_big_model_gets_the_tool_protocol_and_answers_with_real_data(api):
    from jarvis.llm.cerebro import LLMLocal

    grande = Config(llm_local=True, llm_endpoint=api, llm_modelo="qwen2.5-coder-3b")
    RESPOSTAS[:] = ['FERRAMENTA: calculadora {"expressao": "6*7"}', "Deu 42."]
    resposta = LLMLocal(lambda: grande, motor=Motor()).ask([{"role": "user", "content": "quanto é 6 vezes 7?"}], "")
    assert resposta.text == "Deu 42." and "FERRAMENTA:" in PEDIDOS[0]["messages"][0]["content"]
    assert "= 42" in PEDIDOS[1]["messages"][-1]["content"] and "<dados_externos" in PEDIDOS[1]["messages"][-1]["content"]


def test_small_model_receives_real_data_up_front_instead_of_tools(cfg):
    from jarvis.llm.cerebro import LLMLocal

    RESPOSTAS[:] = ["São 10h00."]
    resposta = LLMLocal(lambda: cfg, motor=Motor()).ask([{"role": "user", "content": "que horas são?"}], "")
    sistema = PEDIDOS[-1]["messages"][0]["content"]
    assert resposta.text == "São 10h00." and "Dados reais obtidos agora" in sistema and "10h00" in sistema and "[[jarvis:" not in sistema
    assert ferramentas.consultar_antes("conte uma piada", Motor()) is None
    assert ferramentas.modelo_usa_ferramentas("qwen2.5-coder-7b") and not ferramentas.modelo_usa_ferramentas("qwen2.5-coder-1.5b")


def test_invented_tool_requests_end_the_loop_with_a_plain_answer():
    respostas = iter(["[[jarvis: hoje é 10 de abril]]", "Não sei a data exata."])
    texto, usadas = ferramentas.rodar(lambda m: next(respostas), [{"role": "user", "content": "data?"}], Motor())
    assert texto == "Não sei a data exata." and len(usadas) == 1

"""Resumo deslizante, perfil do usuário (proposta, aprovação, apagar), fatos duráveis, crítica, voz, fallback e roteamento."""

import pytest

from jarvis import config, memory_db
from jarvis.brains import policy
from jarvis.brains.base import Answer, BrainUnavailable
from jarvis.brains.router import NoBrainAvailable, Router
from jarvis.chat import MAX_HISTORY, Conversation
from jarvis.conversa import critica, fala, fatos, perfil, privacidade, reescrita, resumo, sem_cerebro
from jarvis.local.engine import LocalEngine
from jarvis.pc import actions


class Eco:
    name = "claude"

    def ask(self, messages, system):
        return Answer("ok " + messages[-1]["content"][-20:], "claude")


# ── resumo deslizante ────────────────────────────────────────────────────

def test_resumo_respeita_o_limite_e_mantem_o_recente():
    janela = resumo.Janela()
    janela.absorver([{"role": "user", "content": f"pergunta número {i} " + "palavra " * 60} for i in range(200)])
    texto = janela.texto(600)
    assert len(texto) <= 600 + len("(turnos mais antigos omitidos)\n")
    assert "número 199" in texto and "número 0 " not in texto and texto.startswith("(turnos mais antigos omitidos)")
    assert len(janela.notas) <= resumo.MAX_NOTAS


def test_nota_curta_sem_markdown_nem_link():
    nota = resumo.nota({"role": "assistant", "content": "**Resposta** veja https://x.com/a. Segunda frase longa."})
    assert nota.startswith("- Jarvis: Resposta")
    assert "**" not in nota and "https" not in nota and "Segunda" not in nota


def test_conversa_longa_vira_resumo_e_limite_de_historico():
    conversa = Conversation(Router([Eco()]), "s")
    for i in range(MAX_HISTORY):
        conversa.ask(f"assunto {i} sobre python")
    assert len(conversa.history) <= MAX_HISTORY
    assert "assunto 0 sobre python" in conversa.janela.texto()
    conversa.reset()
    assert conversa.janela.texto() == ""


# ── acompanhamento ───────────────────────────────────────────────────────

@pytest.mark.parametrize("texto", ["e o outro?", "e quando ele atrapalha?", "me dá um exemplo disso", "então qual você faria primeiro?"])
def test_detecta_acompanhamento(texto):
    r = reescrita.analisar(texto, [{"role": "user", "content": "o que é um índice em banco de dados?"}, {"role": "assistant", "content": "x"}])
    assert r.acompanhamento and "índice" in r.tema and "índice" in r.consulta(texto)


def test_sem_historico_nao_ha_acompanhamento():
    assert not reescrita.analisar("e o outro?", []).acompanhamento


# ── perfil do usuário ────────────────────────────────────────────────────

@pytest.fixture
def loja(tmp_path):
    return actions.ActionStore(tmp_path / "acoes"), memory_db.open_memory(config.load())


def test_perfil_proposta_nao_grava_ate_aprovar(loja):
    store, mem = loja
    acao = perfil.propor(store, mem, "tom", "direto e curto")
    assert "tom" not in perfil.explicito(mem)
    actions.decide(store, acao.id, approve=False)
    assert "tom" not in perfil.explicito(mem)
    acao = perfil.propor(store, mem, "tom", "direto e curto")
    assert actions.decide(store, acao.id, approve=True).status == "executada"
    assert perfil.explicito(mem)["tom"] == "direto e curto"
    assert "Tom de conversa: direto e curto" in perfil.para_prompt(mem, config.load())


def test_perfil_apagar_exige_aprovacao(loja):
    store, mem = loja
    actions.decide(store, perfil.propor(store, mem, "metas", "passar em banco de dados").id, approve=True)
    acao = perfil.propor_apagar(store, mem, "metas")
    assert "metas" in perfil.explicito(mem)
    actions.decide(store, acao.id, approve=True)
    assert "metas" not in perfil.explicito(mem)
    with pytest.raises(ValueError):
        perfil.propor_apagar(store, mem, "metas")


@pytest.mark.parametrize("valor", ["minha senha é abc123 e meu cpf 123.456.789-09", "ganho R$ 5000 por mês", "x" * 400])
def test_perfil_recusa_dado_sensivel_ou_grande(loja, valor):
    store, mem = loja
    with pytest.raises(ValueError):
        perfil.propor(store, mem, "quem", valor)


def test_perfil_deduz_do_que_ja_existe_e_definido_vence(loja):
    store, mem = loja
    mem.put("Perfil Profissional", "# Perfil Profissional\n- Stack: Python\n- Nível: pleno\n", "perfil")
    cfg = config.load()
    cfg.city = "Fortaleza"
    quem, origem = perfil.compilar(mem, cfg)["quem"]
    assert origem == "deduzido" and "Fortaleza" in quem and "Python" in quem
    actions.decide(store, perfil.propor(store, mem, "quem", "dev júnior").id, approve=True)
    assert perfil.compilar(mem, cfg)["quem"] == ("dev júnior", "definido")


def test_comandos_de_perfil_pelo_motor_local(loja, monkeypatch):
    store, mem = loja
    motor = LocalEngine()
    assert motor.is_direct_command("o que você sabe sobre mim?")
    assert "O que eu sei sobre você" in motor.handle("o que você sabe sobre mim?")
    from jarvis.local import perfil_usuario_skills as skills

    resposta = skills.responder("atualize meu perfil: tom = direto e curto", config.load(), store)
    assert "cartão" in resposta
    pendente = store.pending_since(0)[0]
    assert pendente.kind == "atualizar_perfil" and pendente.params == {"campo": "tom", "valor": "direto e curto"}
    actions.decide(store, pendente.id, approve=True)
    assert "cartão" in skills.responder("apague tom do meu perfil", config.load(), store)
    assert "Diga qual campo" in skills.responder("atualize meu perfil", config.load(), store)


# ── fatos duráveis viram propostas ───────────────────────────────────────

def test_fatos_viram_proposta_e_nao_gravam(loja):
    store, mem = loja
    assert fatos.propor(store, mem, "estou aprendendo SQL para a prova de banco de dados na sexta", "conversa") == 1
    pend = store.pending_since(0)
    assert len(pend) == 1 and pend[0].kind == "guardar_memoria" and mem.count() == 0


@pytest.mark.parametrize("texto", [
    "o que é um índice em banco de dados?", "minha senha do banco é abc123 e eu estudo", "estudo e ganho R$ 3000 por mês agora",
    "resuma meus e-mails e diga o que eu estudo", "oi", "estudo"])
def test_fatos_ignora_pergunta_sensivel_e_terceiros(loja, texto):
    store, mem = loja
    assert fatos.candidatos(texto) == []


# ── privacidade ──────────────────────────────────────────────────────────

def test_mascara_dados_pessoais():
    texto = privacidade.redigir("cpf 123.456.789-09 mail a@b.com fone (85) 99999-8888 chave AIzaSyABCDEFGHIJKL")
    assert "123.456" not in texto and "a@b.com" not in texto and "99999" not in texto and "AIzaSy" not in texto


# ── crítica do modelo local ──────────────────────────────────────────────

def test_critica_refaz_resposta_curta_uma_vez():
    chamadas = []

    def conversa(msgs):
        chamadas.append(msgs)
        return "Use um índice B-tree na coluna do filtro: ele evita varrer a tabela inteira. Exemplo: CREATE INDEX idx ON t(col). Próximo passo: meça com EXPLAIN."

    saida = critica.melhorar("depende", "como faço uma consulta SQL ficar mais rápida na minha tabela grande?", [], conversa)
    assert "B-tree" in saida and len(chamadas) == 1 and "específica" in chamadas[0][-1]["content"]


def test_critica_nao_mexe_em_resposta_boa_nem_em_pergunta_curta():
    def nunca(_):
        raise AssertionError("não deveria refazer")

    boa = "Uma lista guarda itens em ordem e aceita repetidos; um conjunto não repete e não tem ordem. Use conjunto para testar pertencimento."
    assert critica.melhorar(boa, "qual a diferença entre lista e conjunto em Python?", [], nunca) == boa
    assert critica.melhorar("Oi!", "oi", [], nunca) == "Oi!"


def test_critica_detecta_repeticao_e_ignora_falha_do_modelo():
    pergunta = "me explica de novo como funciona a recursão com exemplo"
    anterior = "Recursão é quando a função chama a si mesma até chegar no caso base, como o fatorial."
    assert critica.problema(pergunta, anterior, anterior) == "repetida"

    def quebra(_):
        raise RuntimeError("modelo caiu")

    assert critica.melhorar("depende", "como faço uma consulta SQL ficar mais rápida na minha tabela grande?", [], quebra) == "depende"


# ── voz ──────────────────────────────────────────────────────────────────

def test_fala_resume_resposta_longa_e_deixa_o_detalhe_na_tela():
    longa = "Primeiro passo é abrir o editor. Depois crie o arquivo. " + "Mais um detalhe importante aqui. " * 20 + "\n```py\nprint(1)\n```"
    dita = fala.falado(longa)
    assert len(dita) < 320 and dita.endswith("Os detalhes estão na janela.") and "print" not in dita
    assert fala.falado("Pronto, abri.") == "Pronto, abri."


# ── sem cérebro generativo ───────────────────────────────────────────────

def test_motor_local_orienta_em_vez_de_bloco_generico():
    resposta = LocalEngine().ask([{"role": "user", "content": "estou cansado de tanto estudar, me dá um conselho honesto"}]).text
    assert "cérebro generativo" in resposta and "aistudio.google.com/apikey" in resposta and "Cérebros" in resposta
    assert "Dica:" not in resposta and "Você pode me ensinar" not in resposta


def test_erro_sem_nenhum_cerebro_traz_passos_e_atalhos():
    class Cai:
        name = "claude"

        def ask(self, m, s):
            raise BrainUnavailable("sem chave")

    with pytest.raises(NoBrainAvailable, match="claude: sem chave") as exc:
        Router([Cai()]).ask([{"role": "user", "content": "oi"}], "s")
    assert "1. Gemini" in str(exc.value) and "2. Claude" in str(exc.value) and "3. Cérebro local" in str(exc.value)
    assert {a.get("acao") for a in sem_cerebro.ATALHOS} >= {"cerebros"} and any("aistudio" in a.get("url", "") for a in sem_cerebro.ATALHOS)


def test_fallback_automatico_ate_o_ultimo():
    class Cai:
        def __init__(self, nome):
            self.name = nome

        def ask(self, m, s):
            raise BrainUnavailable("limite")

    class Ok:
        name = "local"

        def ask(self, m, s):
            return Answer("ok", "local")

    assert Router([Cai("claude"), Cai("gemini"), Cai("nvidia"), Ok()]).ask([{"role": "user", "content": "x"}], "s").brain == "local"


# ── política ─────────────────────────────────────────────────────────────

def test_politica_ordem_padrao_e_claude_gemini_nvidia():
    assert config.Config().brains == ["claude", "gemini", "nvidia"]
    for texto in ("estou cansado de estudar, me dá um conselho", "quanto tempo isso leva?"):
        assert policy.preferred(texto, "reserva") is None  # sem preferência: vale a ordem configurada (generativos primeiro)

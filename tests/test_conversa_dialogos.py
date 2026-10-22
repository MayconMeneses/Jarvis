"""30 diálogos de exemplo pelo pipeline real (Conversation + Router + política) com um cérebro FALSO que só registra o que recebe.

Nenhuma IA real é chamada. Verifica o que o cérebro generativo recebe: persona, perfil, histórico, resumo, RAG, data; que a
conversa aberta chega a ele e que comandos exatos e autoconhecimento continuam no motor local.
"""

import json
from pathlib import Path

import pytest

from jarvis import config, memory_db
from jarvis.__main__ import system_prompt
from jarvis.brains import build_router
from jarvis.brains.base import Answer
from jarvis.chat import Conversation

DIALOGOS = json.loads((Path(__file__).parent / "dados" / "dialogos_conversa.json").read_text(encoding="utf-8"))


class Falso:
    def __init__(self, nome):
        self.name, self.chamadas = nome, []

    def ask(self, messages, system):
        self.chamadas.append((list(messages), system))
        return Answer(f"resposta {self.name}", self.name)


@pytest.fixture
def montagem():
    cfg = config.load()
    mem = memory_db.open_memory(cfg)
    mem.remember("Preferência de estudo", "Prefere exemplos práticos; estuda SQL e Python à noite.")
    mem.put("Perfil Profissional", "# Perfil Profissional\n- Stack: Python, JavaScript\n- Nível: júnior\n", "perfil")
    roteador = build_router(cfg)
    claude, local = Falso("claude"), Falso("local")
    roteador.brains = [claude, local]
    return Conversation(roteador, lambda: system_prompt(config.load())), claude, local


def test_trinta_dialogos_de_exemplo():
    assert len(DIALOGOS) == 30
    assert sum(1 for d in DIALOGOS if d.get("seguimento")) >= 6


def test_conversa_aberta_chega_ao_cerebro_generativo(montagem):
    conversa, claude, local = montagem
    for d in (d for d in DIALOGOS if d["tipo"] == "aberta"):
        conversa.reset()
        for texto in d["turnos"]:
            assert conversa.ask(texto).brain == "claude", d["id"]
    assert local.chamadas == []


@pytest.mark.parametrize("tipo", ["comando", "autoconhecimento", "perfil"])
def test_comandos_e_autoconhecimento_continuam_locais(montagem, tipo):
    conversa, claude, local = montagem
    for d in (d for d in DIALOGOS if d["tipo"] == tipo):
        assert conversa.ask(d["turnos"][0]).brain == "local", d["id"]
    assert claude.chamadas == []


def test_prompt_traz_persona_perfil_data_e_memoria(montagem):
    conversa, claude, _ = montagem
    conversa.ask("tenho prova de banco de dados na sexta, o que eu devo revisar primeiro?")
    mensagens, sistema = claude.chamadas[-1]
    assert "A primeira frase já responde" in sistema and "UM próximo passo" in sistema  # persona anti-vagueza
    assert "Perfil do usuário" in sistema and "Python, JavaScript" in sistema  # perfil derivado da memória
    assert "Preferência de estudo" in sistema
    ultima = mensagens[-1]["content"]
    assert "Agora:" in ultima and "/20" in ultima  # data e hora
    assert ultima.rstrip().endswith("o que eu devo revisar primeiro?")
    assert "[Mensagem do usuário]" in ultima


def test_acompanhamento_leva_o_assunto_anterior(montagem):
    conversa, claude, _ = montagem
    conversa.ask("me explica o que é docker")
    conversa.ask("ele é parecido com máquina virtual?")
    ultima = claude.chamadas[-1][0][-1]["content"]
    assert "continua o assunto anterior" in ultima and "me explica o que é docker" in ultima
    assert len(claude.chamadas[-1][0]) == 3  # histórico completo (pergunta, resposta, nova pergunta)


def test_pergunta_nova_nao_e_acompanhamento(montagem):
    conversa, claude, _ = montagem
    conversa.ask("me explica o que é docker")
    conversa.ask("qual a diferença entre flexbox e grid em CSS?")
    assert "continua o assunto anterior" not in claude.chamadas[-1][0][-1]["content"]


def test_rag_traz_nota_relevante_e_conhecimento_curado(montagem):
    conversa, claude, _ = montagem
    conversa.ask("como estudo SQL à noite com exemplos práticos?")
    ultima = claude.chamadas[-1][0][-1]["content"]
    assert "Notas do usuário relacionadas" in ultima and "Preferência de estudo" in ultima


def test_canal_de_voz_pede_resposta_curta(montagem):
    conversa, claude, _ = montagem
    conversa.ask("o que é recursão?", canal="voz")
    assert "Canal: voz" in claude.chamadas[-1][0][-1]["content"]
    conversa.ask("o que é recursão?")
    assert "Canal: voz" not in claude.chamadas[-1][0][-1]["content"]


def test_prompt_de_sistema_estavel_entre_perguntas(montagem):
    """A sessão do Claude reinicia se o sistema mudar: o contexto por pergunta não pode ir nele."""
    conversa, claude, _ = montagem
    conversa.ask("me explica o que é docker")
    conversa.ask("como faço um plano de estudo de SQL?")
    assert claude.chamadas[0][1] == claude.chamadas[1][1]


def test_historico_guardado_sem_o_bloco_de_contexto(montagem):
    conversa, _, _ = montagem
    conversa.ask("me explica o que é docker")
    assert conversa.history[0]["content"] == "me explica o que é docker"


def test_nuvem_nao_recebe_nota_de_area_sensivel(montagem):
    conversa, claude, _ = montagem
    memory_db.open_memory(config.load()).put("Finanças/Reserva", "plano de reserva de emergência com investimento mensal", "memoria")
    conversa.ask("como organizo minha reserva de emergência e investimento mensal?")
    assert "Finanças/Reserva" not in claude.chamadas[-1][0][-1]["content"]


def test_dados_pessoais_sao_mascarados_na_nuvem(montagem):
    conversa, claude, _ = montagem
    memory_db.open_memory(config.load()).put("Trabalho/Contato", "contato do cliente joao@empresa.com para o projeto alfa", "memoria")
    conversa.ask("qual o contato do cliente do projeto alfa?")
    ultima = claude.chamadas[-1][0][-1]["content"]
    assert "joao@empresa.com" not in ultima and "[e-mail]" in ultima

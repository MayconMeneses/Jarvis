"""O perfil mostra o que o usuário pediu para lembrar, sem dado sensível, e fica vazio quando não há nada."""

from jarvis import config, memory_db
from jarvis.conversa import perfil


class Memoria:
    """Memória falsa: só o necessário para o perfil."""

    def __init__(self, indice=""):
        self.indice = indice

    def get(self, ref):
        return None

    def list_notes(self, prefixo="", limite=500):
        return []

    def memories(self):
        return []

    def index_text(self):
        return self.indice


def test_perfil_inclui_o_que_pediu_para_lembrar():
    mem = Memoria("- Eu prefiro vagas remotas de back-end: vagas remotas de back-end")
    texto = perfil.para_usuario(mem, config.Config())
    assert "O que você me pediu para lembrar" in texto and "vagas remotas" in texto


def test_perfil_nao_expoe_lembranca_sensivel():
    mem = Memoria("- Minha senha: senha do banco é 12345\n- Café: gosto de café sem açúcar")
    texto = perfil.para_usuario(mem, config.Config())
    assert "12345" not in texto and "café sem açúcar" in texto


def test_perfil_vazio_diz_que_nao_guardou_nada():
    assert "Ainda não guardei" in perfil.para_usuario(Memoria(), config.Config())
    assert perfil.vazio(Memoria(), config.Config())
    assert not perfil.vazio(Memoria("- Café: gosto de café"), config.Config())

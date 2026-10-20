"""Avisos do uso de IA: cota do Claude, orçamento e modelo sem preço. Cada chave vale por janela (avisa uma vez só)."""

from __future__ import annotations

import time

from jarvis.uso import cota, orcamento, servico


def verificar(agora: float | None = None, reg=None) -> list[tuple[str, str]]:
    """Lista de (chave, texto). A chave inclui o início da janela/mês: o agendador não repete o mesmo aviso."""
    agora = agora or time.time()
    reg = reg or servico.atualizar()
    estado, mes = cota.estado(reg, agora), orcamento.mes(reg, agora)
    avisos: list[tuple[str, str]] = []
    for medida, nome in ((estado["janela_5h"], "da janela de 5 h"), (estado["semana"], "semanal")):
        if medida["alerta"]:
            avisos.append((f"uso:cota:{medida['nome']}:{int(medida['inicio'])}",
                           f"⚠️ A cota {nome} do Claude está em cerca de {medida['pct']:.0f}% (estimativa). "
                           "Posso mandar as perguntas simples para o Gemini ou o modo independente até o reset."))
        elif medida["acaba_antes_do_reset"]:
            avisos.append((f"uso:cota-ritmo:{medida['nome']}:{int(medida['inicio'])}",
                           f"⚠️ Nesse ritmo a cota {nome} do Claude acaba antes do reset (estimativa)."))
    if mes["alerta"]:
        avisos.append((f"uso:orcamento:{mes['dias_mes']}:{time.strftime('%Y-%m', time.localtime(agora))}",
                       f"💸 O gasto do mês chegou a {mes['pct']:.0f}% do orçamento (US$ {mes['gasto']:.2f} de US$ {mes['orcamento']:.2f})."))
    elif mes["projecao_estoura"]:
        avisos.append((f"uso:projecao:{time.strftime('%Y-%m', time.localtime(agora))}",
                       f"💸 No ritmo atual o mês termina em US$ {mes['projecao']:.2f}, acima do orçamento de US$ {mes['orcamento']:.2f}."))
    if mes["sem_preco"]:
        avisos.append((f"uso:sempreco:{','.join(mes['sem_preco'])}:{time.strftime('%Y-%m', time.localtime(agora))}",
                       "ℹ️ Modelo sem preço na tabela de uso: " + ", ".join(mes["sem_preco"]) + ". Preencha em Uso de IA > Preços."))
    return avisos

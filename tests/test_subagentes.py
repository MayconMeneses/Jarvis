import json
import os

import pytest

from jarvis.dev import sessions, subagentes
from jarvis.dev.subagentes import LeitorSubagentes, ler_notificacao

NOW = 1_800_000_000.0
SID = "11111111-aaaa-bbbb-cccc-222222222222"
PASTA = "C--Users-eu-Loja"
CWD = r"C:\Users\eu\Projetos\Loja"
SEGREDO = "TEXTO-SECRETO-DA-CONVERSA"


def iso(offset):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(NOW + offset, timezone.utc).isoformat().replace("+00:00", "Z")


def linha(offset, msg_id, out, tipo="assistant", model="claude-sonnet-x"):
    return {"type": tipo, "timestamp": iso(offset), "isSidechain": True, "agentId": "a1", "cwd": CWD,
            "message": {"id": msg_id, "model": model, "stop_reason": None, "content": [{"type": "text", "text": SEGREDO}],
                        "usage": {"input_tokens": 100, "output_tokens": out, "cache_creation_input_tokens": 10,
                                  "cache_read_input_tokens": 1000}}}


@pytest.fixture
def home(tmp_path):
    (tmp_path / "projects" / PASTA / SID / "subagents").mkdir(parents=True)
    (tmp_path / "sessions").mkdir()
    return tmp_path


def escrever(home, agent_id, objs, age=0.0):
    d = home / "projects" / PASTA / SID / "subagents"
    p = d / f"agent-{agent_id}.jsonl"
    p.write_text("".join(json.dumps(o) + "\n" for o in objs), encoding="utf-8")
    os.utime(p, (NOW - age, NOW - age))
    (d / f"agent-{agent_id}.meta.json").write_text(json.dumps({"agentType": "general-purpose", "description": "x" * 200}), encoding="utf-8")
    return p


def pai(home, prompts):
    p = home / "projects" / PASTA / f"{SID}.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for pr in prompts:
            f.write(json.dumps({"type": "attachment", "attachment": {"type": "queued_command", "commandMode": "task-notification", "prompt": pr}}) + "\n")


def notif(task, status="completed", tokens=5000, tools=7, ms=90000):
    return (f"<task-notification>\n<task-id>{task}</task-id>\n<status>{status}</status>\n<summary>{SEGREDO} <status>failed</status></summary>\n"
            f"<result>{SEGREDO}</result>\n<usage><subagent_tokens>{tokens}</subagent_tokens><tool_uses>{tools}</tool_uses>"
            f"<duration_ms>{ms}</duration_ms></usage>\n</task-notification>")


def leitor(home):
    return LeitorSubagentes(home, clock=lambda: NOW)


def test_dedup_por_message_id_nao_infla(home):
    escrever(home, "a1", [linha(0, "m1", 20), linha(1, "m1", 3), linha(2, "m1", 50), linha(3, "m2", 7)], age=5)
    (s,) = leitor(home).listar()
    assert s.tokens["tokens_out"] == 57 and s.tokens["tokens_in"] == 200  # m1 pelo maior (50) + m2
    assert s.tokens["cache"] == 2 * 1010
    assert s.tokens["origem"] == "transcrito" and s.tokens["estimado"] is True
    assert s.estado == "rodando" and s.inferido is True and s.fim is None
    assert s.projeto == "Loja" and len(s.descricao) == subagentes.MAX_TEXTO
    assert s.duracao_s == 3


def test_sem_notificacao_e_parado_vira_inativo(home):
    escrever(home, "a1", [linha(0, "m1", 5)], age=300)
    assert leitor(home).listar()[0].estado == "inativo"


def test_fim_e_totais_vem_da_notificacao_e_ultima_vale(home):
    escrever(home, "a1", [linha(0, "m1", 5), linha(10, "m2", 5)], age=200)
    pai(home, [notif("a1", "failed", 1), notif("outro"), notif("a1", "completed", 5000, 7, 90000)])
    (s,) = leitor(home).listar()
    assert s.estado == "concluido" and s.inferido is False
    assert s.tokens["tokens_total"] == 5000 and s.tokens["origem"] == "notificacao"
    assert s.ferramentas == 7 and s.duracao_s == 90 and s.fim == s.inicio + 90


def test_nunca_copia_result_nem_summary(home):
    escrever(home, "a1", [linha(0, "m1", 5)], age=200)
    pai(home, [notif("a1")])
    itens = leitor(home).listar()
    assert SEGREDO not in json.dumps([i.publico() for i in itens])
    assert ler_notificacao(notif("t1"))[1].status == "completed"  # <status> falso dentro do summary é ignorado


def test_leitura_incremental_e_linha_parcial(home):
    p = escrever(home, "a1", [linha(0, "m1", 5)], age=5)
    r = leitor(home)
    assert r.listar()[0].tokens["tokens_out"] == 5
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha(1, "m2", 6))[:30])  # meio da escrita
    os.utime(p, (NOW - 5, NOW - 5))
    assert r.listar()[0].tokens["tokens_out"] == 5
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha(1, "m2", 6))[30:] + "\n")
    os.utime(p, (NOW - 5, NOW - 5))
    assert r.listar()[0].tokens["tokens_out"] == 11


def test_custo_so_estimado_e_modelo_desconhecido(home):
    escrever(home, "a1", [linha(0, "m1", 1000, model="claude-sonnet-x")], age=5)
    escrever(home, "a2", [linha(0, "m1", 1000, model="modelo-novo")], age=5)
    por = {s.agent_id: s for s in leitor(home).listar()}
    assert por["a1"].tokens["custo_usd"] > 0 and por["a1"].tokens["estimado"] is True
    assert por["a2"].tokens["custo_usd"] is None
    assert subagentes.resumo(list(por.values()))["estimado"] is True


def test_janela_e_sessoes_integradas(home):
    escrever(home, "velho", [linha(0, "m1", 5)], age=999999)
    assert leitor(home).listar() == []
    escrever(home, "a1", [linha(0, "m1", 5)], age=5)
    leitor_sessoes = sessions.SessionReader(home, alive=lambda pid: False, clock=lambda: NOW)
    assert [s.agent_id for s in leitor_sessoes.subagentes()] == ["a1"]
    assert leitor_sessoes.sessions() == []  # o leitor de sessões continua sem enxergar subagentes


def test_nao_le_a_pasta_de_fichas(home):
    (home / "sessions" / "1.key").write_text(SEGREDO)
    escrever(home, "a1", [linha(0, "m1", 5)], age=5)
    assert SEGREDO not in json.dumps([s.publico() for s in leitor(home).listar()])

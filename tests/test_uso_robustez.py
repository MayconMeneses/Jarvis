"""Registro de uso: esquema versionado, concorrência entre threads, coleta incremental e opções de filtro."""

import json
import sqlite3
import threading
import time

from jarvis.uso import coletor_claude, resumo, servico
from jarvis.uso.registro import VERSAO_ESQUEMA, Registro

USO = {"in": 1, "out": 10, "cw": 0, "cw1h": 0, "cr": 0}


def test_banco_antigo_sem_versao_ganha_versao_e_nao_perde_dados(tmp_path):
    caminho = tmp_path / "uso_ia.db"
    reg = Registro(caminho)
    reg.ao_vivo("claude", "claude-opus-5-5", USO)
    reg.fechar()
    with sqlite3.connect(caminho) as db:
        db.execute("PRAGMA user_version=0")  # como ficou nas versões 0.22/0.23
    reg = Registro(caminho)
    assert len(reg.linhas()) == 1
    assert reg._db.execute("PRAGMA user_version").fetchone()[0] == VERSAO_ESQUEMA
    assert reg._db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_banco_de_versao_futura_continua_funcionando(tmp_path):
    caminho = tmp_path / "uso_ia.db"
    Registro(caminho).fechar()
    with sqlite3.connect(caminho) as db:
        db.execute("PRAGMA user_version=99")
    reg = Registro(caminho)
    reg.ao_vivo("claude", "m", USO)
    assert reg._db.execute("PRAGMA user_version").fetchone()[0] == 99


def test_gravacao_concorrente_de_varias_threads_nao_perde_linhas(tmp_path):
    reg = Registro(tmp_path / "uso_ia.db")
    erros = []

    def escrever(n):
        try:
            for i in range(40):
                reg.ao_vivo("gemini", "g", USO, ts=1_700_000_000 + n * 100 + i)
                reg.linhas()
        except Exception as exc:  # pragma: no cover
            erros.append(exc)

    threads = [threading.Thread(target=escrever, args=(n,)) for n in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not erros and len(reg.linhas()) == 240


def test_opcoes_e_vazio_sem_carregar_o_historico(tmp_path):
    reg = Registro(tmp_path / "uso_ia.db")
    assert reg.opcoes() == {"modelos": [], "projetos": [], "provedores": [], "vazio": True}
    reg.inserir(ts=time.time(), fonte="jsonl", provedor="claude", modelo="claude-opus-5-5", projeto="jarvis", uso=USO, chave="a|b")
    reg.ao_vivo("local")
    o = resumo.resumo(reg, "hoje")["opcoes"]
    assert o == {"modelos": ["claude-opus-5-5"], "projetos": ["jarvis"], "provedores": ["claude", "local"]}
    assert resumo.resumo(reg, "hoje")["vazio"] is False


def _linha(msg, saida, ts="2026-10-20T10:00:00Z"):
    return json.dumps({"timestamp": ts, "sessionId": "s1", "cwd": "C:/x/proj", "requestId": "r1",
                       "message": {"id": msg, "model": "claude-opus-5-5", "usage": {"input_tokens": 1, "output_tokens": saida}}}) + "\n"


def test_coleta_incremental_ignora_linha_incompleta_e_nao_duplica(tmp_path):
    raiz, reg = tmp_path / "projects", Registro(tmp_path / "uso_ia.db")
    (raiz / "p").mkdir(parents=True)
    arq = raiz / "p" / "s1.jsonl"
    arq.write_text(_linha("m1", 5) + _linha("m1", 9)[:40], encoding="utf-8")  # a 2ª linha ainda está sendo escrita
    assert coletor_claude.coletar(reg, raiz)["linhas"] == 1
    with open(arq, "a", encoding="utf-8") as f:
        f.write(_linha("m1", 9)[40:])
    coletor_claude.coletar(reg, raiz)
    coletor_claude.coletar(reg, raiz)  # sem novidade: não relê nem repete
    [linha] = reg.linhas()
    assert linha["tout"] == 9 and linha["projeto"] == "proj"


def test_coletas_simultaneas_nao_duplicam_linhas_sem_chave(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_CLAUDE_PROJECTS", str(tmp_path / "projects"))
    (tmp_path / "projects" / "p").mkdir(parents=True)
    linha = json.loads(_linha("m", 3))
    linha["message"].pop("id")  # sem id não há chave de dedupe: só a trava de coleta evita repetir
    (tmp_path / "projects" / "p" / "s.jsonl").write_text(json.dumps(linha) + "\n", encoding="utf-8")
    monkeypatch.setattr("jarvis.uso.servico.caminho_padrao", lambda: tmp_path / "uso_ia.db")
    ts = [threading.Thread(target=servico.atualizar, kwargs={"forcar": True}) for _ in range(5)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(servico.registro().linhas()) == 1


def test_coleta_em_blocos_pequenos_le_tudo_e_linha_gigante_e_descartada(tmp_path, monkeypatch):
    monkeypatch.setattr(coletor_claude, "BLOCO", 64)  # força várias leituras, com linhas cortadas no meio
    monkeypatch.setattr(coletor_claude, "MAX_LINHA", 5000)
    raiz, reg = tmp_path / "projects", Registro(tmp_path / "uso_ia.db")
    (raiz / "p").mkdir(parents=True)
    texto = "".join(_linha(f"m{i}", i + 1, f"2026-10-20T10:00:{i:02d}Z") for i in range(20))
    gigante = '{"x": "' + "a" * 6000 + '"}\n'
    (raiz / "p" / "s.jsonl").write_text(texto + gigante + _linha("fim", 99), encoding="utf-8")
    assert coletor_claude.coletar(reg, raiz)["linhas"] >= 20
    assert len(reg.linhas()) >= 20 and max(l["tout"] for l in reg.linhas()) >= 20
    posicao, _ = reg.posicao(str(raiz / "p" / "s.jsonl"))
    assert posicao > 0
    coletor_claude.coletar(reg, raiz)
    assert reg.posicao(str(raiz / "p" / "s.jsonl"))[0] == posicao  # nada novo: não relê

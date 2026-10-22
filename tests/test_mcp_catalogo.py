"""Catálogo curado de ferramentas externas: versões fixadas, integridade, cartão de instalação, mcp.json só com aprovados e reinício da sessão."""

import copy
import json
import sys

import pytest

from jarvis import brains
from jarvis.brains.claude_cli import ClaudeCLI
from jarvis.brains.claude_session import ClaudeSession
from jarvis.config import ClaudeConfig, data_dir
from jarvis.local.engine import LocalEngine
from jarvis.mcp_catalogo import cartoes, catalogo, instalados, integridade, saude
from jarvis.pc import actions
from tests.test_claude_session import FakeProc, ok

NPM = next(i for i in catalogo.itens() if i["gerenciador"] == "npx")
PYPI = next(i for i in catalogo.itens() if i["gerenciador"] == "uvx")


def com(item, **mudancas):
    novo = copy.deepcopy(item)
    novo.update(mudancas)
    return novo


# ── o catálogo ───────────────────────────────────────────────────────────
def test_every_catalog_entry_is_valid_pinned_and_documented():
    ids = [i["id"] for i in catalogo.itens()]
    assert len(ids) == len(set(ids)) >= 3
    for item in catalogo.itens():
        catalogo.validar_item(item)
        assert item["risco"] in ("baixo", "medio") and item["riscos"] and item["permissoes"] and item["motivo"]
        assert item["fonte"].startswith("https://github.com/modelcontextprotocol/") and item["mantenedor"].startswith("modelcontextprotocol")


def test_dangerous_servers_are_refused_with_a_reason_and_are_not_installable():
    recusados = {r["pacote"] for r in catalogo.recusados()}
    for perigoso in ("@modelcontextprotocol/server-filesystem", "@wonderwhy-er/desktop-commander", "@playwright/mcp"):
        assert perigoso in recusados
    assert all(r["motivo"] for r in catalogo.recusados())
    instalaveis = {i["pacote"] for i in catalogo.itens()}
    assert not instalaveis & recusados and all("filesystem" not in p and "commander" not in p for p in instalaveis)


@pytest.mark.parametrize("mudanca", [
    {"versao": "^1.2.3"}, {"versao": "latest"}, {"versao": "1.x"}, {"versao": ""}, {"pacote": "pkg; rm -rf /"}, {"pacote": "pkg --registry=http://evil"},
    {"gerenciador": "pip"}, {"gerenciador": "powershell"}, {"risco": "alto"}, {"riscos": []}, {"args": ["--ok", "-x y"]}, {"args": ["rm -rf /"]},
    {"env": {"minuscula": "x"}}, {"fonte": "https://evil.example/repo"}, {"registro": "https://evil.example/p"}, {"integridade": {}},
])
def test_invalid_entries_are_rejected(mudanca):
    with pytest.raises(catalogo.CatalogoInvalido):
        catalogo.validar_item(com(NPM, **mudanca))


def test_missing_integrity_and_fields_are_rejected():
    with pytest.raises(catalogo.CatalogoInvalido):
        catalogo.validar_item(com(NPM, integridade={"tipo": "sha512", "valor": "sha512-curto"}))
    with pytest.raises(catalogo.CatalogoInvalido):
        catalogo.validar_item(com(PYPI, integridade={"tipo": "sha256", "arquivos": {"a.whl": "123"}}))
    incompleto = dict(NPM)
    del incompleto["permissoes"]
    with pytest.raises(catalogo.CatalogoInvalido):
        catalogo.validar_item(incompleto)


def test_command_is_exact_and_hardened(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    programa, args, env = catalogo.comando(NPM, "/dados")
    assert programa == "npx" and args[:2] == ["-y", f"{NPM['pacote']}@{NPM['versao']}"] and env["npm_config_ignore_scripts"] == "true"
    programa, args, env = catalogo.comando(PYPI, "/dados")
    assert programa == "uvx" and args == ["--no-build", f"{PYPI['pacote']}=={PYPI['versao']}"]
    memoria = catalogo.achar("memoria")
    assert catalogo.comando(memoria, "/dados")[2]["MEMORY_FILE_PATH"] == "/dados/mcp-memoria.jsonl"
    monkeypatch.setattr(sys, "platform", "win32")
    assert catalogo.comando(NPM, "")[:2] == ("cmd", ["/c", "npx", "-y", f"{NPM['pacote']}@{NPM['versao']}"])


def test_lookup_by_name_id_or_part_of_name():
    assert catalogo.achar("memória")["id"] == "memoria_grafo" and catalogo.achar("tempo")["id"] == "tempo" and catalogo.achar("fetch")["id"] == "leitura_pagina"
    assert catalogo.achar("") is None and catalogo.achar("zzzz-nada") is None


# ── integridade no registro ──────────────────────────────────────────────
class Resp:
    def __init__(self, dados):
        self._d = json.dumps(dados).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return self._d


def registro(dados):
    return lambda pedido, timeout=0: Resp(dados)


def test_integrity_matches_npm_and_pypi_and_detects_tampering():
    assert integridade.verificar(NPM, registro({"dist": {"integrity": NPM["integridade"]["valor"]}})).ok
    assert not integridade.verificar(NPM, registro({"dist": {"integrity": "sha512-" + "A" * 86 + "=="}})).ok
    assert not integridade.verificar(NPM, registro({"dist": {"integrity": NPM["integridade"]["valor"]}, "deprecated": "morto"})).ok
    certos = [{"filename": f, "digests": {"sha256": h}} for f, h in PYPI["integridade"]["arquivos"].items()]
    assert integridade.verificar(PYPI, registro({"urls": certos})).ok
    adulterado = [dict(certos[0], digests={"sha256": "0" * 64}), certos[1]]
    assert not integridade.verificar(PYPI, registro({"urls": adulterado})).ok
    assert not integridade.verificar(PYPI, registro({"urls": [dict(c, yanked=True) for c in certos]})).ok


def test_integrity_fails_closed_without_network_or_with_garbage():
    def cai(*a, **k):
        raise OSError("sem rede")

    assert not integridade.verificar(NPM, cai).ok
    assert not integridade.verificar(PYPI, registro(["lixo"])).ok


def test_registry_urls_are_fixed_hosts():
    vistos = []

    def espia(pedido, timeout=0):
        vistos.append(pedido.full_url)
        return Resp({"dist": {"integrity": ""}, "urls": []})

    integridade.verificar(NPM, espia)
    integridade.verificar(PYPI, espia)
    assert vistos[0].startswith("https://registry.npmjs.org/") and "%2F" in vistos[0] and vistos[1].startswith("https://pypi.org/pypi/")


# ── cartão: nada executa antes de aprovar ────────────────────────────────
@pytest.fixture
def ambiente(monkeypatch):
    chamadas = {"testar": 0, "verificar": 0}
    monkeypatch.setattr(saude, "prerequisito", lambda g: (f"/bin/{g}", f"{g} encontrado."))

    def verificar_ok(item, opener=None):
        chamadas["verificar"] += 1
        return integridade.Verificacao(True, "Hash confere.")

    def teste_ok(programa, args, env, tempo=0):
        chamadas["testar"] += 1
        return saude.Saude(True, "o servidor respondeu e listou 2 ferramenta(s)", ["a", "b"])

    monkeypatch.setattr(integridade, "verificar", verificar_ok)
    monkeypatch.setattr(saude, "testar", teste_ok)
    return chamadas


def propor(termo):
    return cartoes.propor_instalar(termo, actions.ActionStore())


def test_install_proposal_shows_source_version_permissions_risks_and_executes_nothing(ambiente):
    texto = propor("memória")
    (cartao,) = actions.ActionStore().pending_since(0)
    d = cartao.descricao
    for trecho in ("github.com/modelcontextprotocol", "1.0.0", "Permissões", "Risco baixo", "Comando exato", "@modelcontextprotocol/server-memory@1.0.0", "MIT"):
        assert trecho in d, trecho
    assert cartao.kind == "instalar_mcp" and cartao.status == "pendente" and texto.startswith("Preparei o cartão")
    assert ambiente["testar"] == 0 and instalados.ler()["itens"] == [] and not (data_dir() / "mcp_instalados.json").exists()
    assert not (data_dir() / "mcp.json").exists()


def test_missing_prerequisite_explains_how_to_install_and_makes_no_card(monkeypatch, ambiente):
    monkeypatch.setattr(saude, "prerequisito", lambda g: (None, f"Falta o {g}. " + saude.COMO_INSTALAR[g]))
    assert "winget" in propor("tempo") and actions.ActionStore().pending_since(0) == []


def test_tampered_package_or_offline_registry_makes_no_card(monkeypatch, ambiente):
    monkeypatch.setattr(integridade, "verificar", lambda item, opener=None: integridade.Verificacao(False, "O pacote NÃO bate."))
    assert "NÃO bate" in propor("tempo") and actions.ActionStore().pending_since(0) == []


def test_unknown_tool_lists_the_catalog_and_arbitrary_text_is_never_a_command(ambiente):
    texto = propor("npx -y pacote-malicioso && calc.exe")
    assert "Não conheço" in texto and "Hora e fusos" in texto and actions.ActionStore().pending_since(0) == [] and ambiente["testar"] == 0


def test_approval_verifies_tests_registers_and_writes_only_approved_servers(ambiente):
    propor("tempo")
    cartao = actions.ActionStore().pending_since(0)[0]
    feito = actions.decide(actions.ActionStore(), cartao.id, approve=True)
    assert feito.status == "executada" and "instalada e testada" in feito.resultado and ambiente["verificar"] >= 2 and ambiente["testar"] == 1
    config = json.loads((data_dir() / "mcp.json").read_text(encoding="utf-8"))
    assert set(config["mcpServers"]) == {"jarvis", "ext_tempo"}
    bloco = config["mcpServers"]["ext_tempo"]
    assert "mcp-server-time==2026.8.18" in bloco["args"] and "--no-build" in bloco["args"]
    assert instalados.ler()["itens"][0]["ferramentas"] == ["a", "b"] and instalados.ler()["historico"][0]["acao"] == "instalou"


def test_declined_card_changes_nothing(ambiente):
    propor("tempo")
    cartao = actions.ActionStore().pending_since(0)[0]
    assert actions.decide(actions.ActionStore(), cartao.id, approve=False).status == "recusada"
    assert instalados.ler()["itens"] == [] and ambiente["testar"] == 0 and not (data_dir() / "mcp.json").exists()


def test_failed_health_test_or_integrity_at_approval_installs_nothing(monkeypatch, ambiente):
    propor("tempo")
    cartao = actions.ActionStore().pending_since(0)[0]
    monkeypatch.setattr(saude, "testar", lambda *a, **k: saude.Saude(False, "o servidor não respondeu"))
    r = actions.decide(actions.ActionStore(), cartao.id, approve=True)
    assert r.status == "falhou" and "Nada foi ligado" in r.resultado and instalados.ler()["itens"] == []
    propor("pensamento")
    monkeypatch.setattr(integridade, "verificar", lambda item, opener=None: integridade.Verificacao(False, "hash diferente"))
    outro = [a for a in actions.ActionStore().pending_since(0) if a.params["id"] == "pensamento"][0]
    assert actions.decide(actions.ActionStore(), outro.id, approve=True).status == "falhou" and instalados.ler()["itens"] == []


def test_forged_card_with_unknown_id_or_stale_version_is_refused(ambiente):
    loja = actions.ActionStore()
    falso = loja.save(actions.Action("instalar_mcp", {"id": "calc && del", "versao": "1.0.0"}, "d", "m"))
    velho = loja.save(actions.Action("instalar_mcp", {"id": "tempo", "versao": "1.0.0"}, "d", "m"))
    assert actions.decide(loja, falso.id, approve=True).status == "falhou" and actions.decide(loja, velho.id, approve=True).status == "falhou"
    assert instalados.ler()["itens"] == [] and ambiente["testar"] == 0


def instalar(termo):
    propor(termo)
    cartao = [a for a in actions.ActionStore().pending_since(0) if a.params["id"] == catalogo.achar(termo)["id"] and a.status == "pendente"][0]
    assert actions.decide(actions.ActionStore(), cartao.id, approve=True).status == "executada"


def test_deactivate_and_remove_by_card_update_the_config(ambiente):
    instalar("tempo")
    instalar("pensamento")
    loja = actions.ActionStore()
    cartoes.propor_remover("tempo", loja, desativar=True)
    cartoes.propor_remover("pensamento", loja)
    for c in [a for a in loja.pending_since(0) if a.kind == "remover_mcp"]:
        assert actions.decide(loja, c.id, approve=True).status == "executada"
    assert set(json.loads((data_dir() / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]) == {"jarvis"}
    assert [(i["id"], i["ativo"]) for i in instalados.ler()["itens"]] == [("tempo", False)]
    assert "desativada" in instalados.resumo()
    assert [h["acao"] for h in instalados.ler()["historico"]][-2:] == ["desativou", "removeu"]
    assert "não está instalada" in cartoes.propor_remover("memoria", loja)


def test_registered_version_that_no_longer_matches_the_catalog_is_not_launched(ambiente):
    instalar("tempo")
    dados = instalados.ler()
    dados["itens"][0]["versao"] = "2025.1.1"
    (data_dir() / "mcp_instalados.json").write_text(json.dumps(dados), encoding="utf-8")
    assert instalados.servidores() == {} and "desatualizada" in instalados.resumo()


def test_tampered_registry_file_cannot_inject_commands(ambiente):
    (data_dir() / "mcp_instalados.json").parent.mkdir(parents=True, exist_ok=True)
    (data_dir() / "mcp_instalados.json").write_text(json.dumps({"itens": [{"id": "calc.exe", "versao": "1", "ativo": True, "command": "calc.exe"}]}), encoding="utf-8")
    assert instalados.servidores() == {}


# ── Claude CLI: --mcp-config e reinício da sessão ────────────────────────
def test_claude_cli_allows_only_jarvis_and_approved_external_servers(ambiente, tmp_path):
    instalar("tempo")
    caminho = brains.write_mcp_config(tmp_path / "mcp.json")
    comando = ClaudeCLI(ClaudeConfig(executable="claude"), mcp_config=caminho).command("sys")
    assert comando[comando.index("--allowedTools") + 1] == "mcp__jarvis,mcp__ext_tempo" and "--strict-mcp-config" in comando
    sem = ClaudeCLI(ClaudeConfig(executable="claude"), mcp_config=None).command("sys")
    assert "--mcp-config" not in sem and "--allowedTools" not in sem


def test_persistent_session_restarts_when_an_external_tool_is_installed(ambiente, tmp_path):
    caminho = brains.write_mcp_config(tmp_path / "mcp.json")
    FakeProc.instances, FakeProc.next_replies = [], [ok("a"), ok("b"), ok("c")]
    sessao = ClaudeSession(ClaudeConfig(executable="x", timeout_seconds=5), workdir=tmp_path, mcp_config=caminho, popen=FakeProc)

    def u(t):
        return {"role": "user", "content": t}

    primeira = sessao.ask([u("um")], "sys")
    sessao.ask([u("um"), {"role": "assistant", "content": primeira.text}, u("dois")], "sys")
    assert len(FakeProc.instances) == 1  # nada mudou: o mesmo processo
    instalar("tempo")
    brains.write_mcp_config(caminho)
    sessao.ask([u("um"), {"role": "assistant", "content": "b"}, u("três")], "sys")
    assert len(FakeProc.instances) == 2 and "mcp__ext_tempo" in " ".join(FakeProc.instances[1].cmd)

// Projetos prontos: o celular tem que gerar exatamente o que o PC gera (jarvis.dev.modelos.arquivos).
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { arquivosDoModelo, listarModelos, nomeSeguro, slug } from "../js/modelos.js";
import { caminhoSeguro, MAX_CHARS } from "../js/oficina-espaco.js";

const modelos = JSON.parse(readFileSync(new URL("../dados/modelos.json", import.meta.url), "utf8"));
const raiz = fileURLToPath(new URL("../../", import.meta.url));
const python = [process.env.PYTHON, "python", "python3"].filter(Boolean).find((p) => spawnSync(p, ["-c", "import jarvis.dev.modelos"], { cwd: raiz }).status === 0);

test("slug e nome seguro seguem as regras do PC", () => {
  assert.equal(slug("Minha Loja Ótima!"), "minha-loja-otima");
  assert.equal(slug("***"), "projeto");
  assert.equal(nomeSeguro("A<b>\"c\" {d} $e \\f"), "Abc d e f");
  assert.equal(nomeSeguro("<>"), "Projeto");
});

test("os 8 modelos existem, sem marcadores sobrando e com caminhos que a Oficina aceita", () => {
  assert.equal(listarModelos(modelos).length, 8);
  for (const id of Object.keys(modelos)) {
    const arquivos = arquivosDoModelo(modelos, id, "Loja Boa", "Vende coisas");
    assert.ok(Object.keys(arquivos).length >= 4, id);
    for (const [c, t] of Object.entries(arquivos)) {
      assert.doesNotMatch(t, /__NOME__|__SLUG__|__DESCRICAO__|XNOMEX|xnomex|XDESCX/, `${id}/${c}`);
      assert.equal(caminhoSeguro(c), c);
      assert.ok(t.length <= MAX_CHARS, `${id}/${c} passa do limite da Oficina`);
    }
  }
  assert.throws(() => arquivosDoModelo(modelos, "cobol", "x"), /modelo/);
});

test("nome, slug e descrição entram nos arquivos; README usa o nome cru e descrição padrão", () => {
  const a = arquivosDoModelo(modelos, "fastapi", "  Meu App <x>  ", "");
  assert.match(a["backend/main.py"], /Meu App x/);
  assert.match(a["README.md"], /^# Meu App <x>\n\nProjeto criado pela Jarvis/);
});

test("paridade com jarvis.dev.modelos.arquivos (Python)", { skip: !python && "Python com o pacote jarvis não encontrado" }, () => {
  const casos = [["Minha Loja Ótima", "Vende coisas  "], ["A<b>\"c\" {d} $e", ""], ["  Café & Cia  ", "Sistema de pedidos"], ["***", "x"]];
  for (const id of Object.keys(modelos)) {
    for (const [nome, texto] of casos) {
      const codigo = "import json,sys; from jarvis.dev import modelos; a=json.loads(sys.stdin.read()); print(json.dumps(modelos.arquivos(a[0],a[1],a[2]),ensure_ascii=False))";
      const r = spawnSync(python, ["-X", "utf8", "-c", codigo], { cwd: raiz, input: JSON.stringify([id, nome, texto]), encoding: "utf8" });
      assert.equal(r.status, 0, r.stderr);
      assert.deepEqual(arquivosDoModelo(modelos, id, nome, texto), JSON.parse(r.stdout), `${id} / ${nome}`);
    }
  }
});

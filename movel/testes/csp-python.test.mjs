// CSP do ambiente do Python (Pyodide): verificada de verdade no Chromium em 2026-10-20 (print + ls via executar, saída 3.14.2); aqui só se garante que não afrouxa.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const html = (n) => readFileSync(new URL(`../sandbox/${n}`, import.meta.url), "utf8");
const csp = (n) => /Content-Security-Policy" content="([^"]+)"/.exec(html(n))[1];
const diretivas = (n) => Object.fromEntries(csp(n).split(";").map((d) => d.trim().split(/\s+/)).map(([k, ...v]) => [k, v]));

test("Python: só o diretório /pyodide/ do jsDelivr, sem curinga nem o CDN inteiro", () => {
  const d = diretivas("py.html");
  assert.deepEqual(d["default-src"], ["'none'"]);
  assert.deepEqual(d["connect-src"], ["https://cdn.jsdelivr.net/pyodide/"]);
  assert.ok(d["script-src"].includes("https://cdn.jsdelivr.net/pyodide/"));
  assert.ok(d["script-src"].includes("'wasm-unsafe-eval'"));
  assert.deepEqual(d["worker-src"], ["blob:"]);
  for (const v of Object.values(d).flat()) {
    assert.notEqual(v, "*"); assert.notEqual(v, "https:"); assert.notEqual(v, "https://cdn.jsdelivr.net"); assert.notEqual(v, "https://cdn.jsdelivr.net/");
    assert.doesNotMatch(v, /jsdelivr\.net\/(npm|gh)/);
  }
});

test("JavaScript: sem rede nenhuma", () => {
  const d = diretivas("js.html");
  assert.deepEqual(d["default-src"], ["'none'"]);
  assert.ok(!d["connect-src"] || d["connect-src"].join() === "'none'");
});

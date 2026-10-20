// Código que roda DENTRO do ambiente isolado (um Worker dentro de um iframe sem acesso a nada do app). Cada função abaixo é
// convertida em texto e vira o Worker; por isso elas não podem usar nada de fora (só o que está dentro delas).

export function trabalhadorJs() {
  const enviar = (linha) => postMessage({ tipo: "saida", linha });
  const fmt = (v) => { if (typeof v === "string") return v; try { return JSON.stringify(v); } catch (e) { return String(v); } };
  console.log = console.info = console.debug = (...a) => enviar(a.map(fmt).join(" "));
  console.error = console.warn = (...a) => enviar("[erro] " + a.map(fmt).join(" "));
  self.fetch = undefined; self.XMLHttpRequest = undefined; self.WebSocket = undefined; self.importScripts = undefined;

  const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const falhar = (msg, padrao) => { const e = new Error(msg || padrao); e.name = "AssertionError"; throw e; };
  const assert = (v, msg) => { if (!v) falhar(msg, "a condição é falsa"); };
  assert.ok = assert;
  assert.equal = (a, b, msg) => { if (a != b) falhar(msg, `esperava ${fmt(b)}, veio ${fmt(a)}`); };  // eslint-disable-line eqeqeq
  assert.strictEqual = (a, b, msg) => { if (a !== b) falhar(msg, `esperava ${fmt(b)}, veio ${fmt(a)}`); };
  assert.notEqual = assert.notStrictEqual = (a, b, msg) => { if (a === b) falhar(msg, `não deveria ser ${fmt(b)}`); };
  assert.deepEqual = assert.deepStrictEqual = (a, b, msg) => { if (!igual(a, b)) falhar(msg, `esperava ${fmt(b)}, veio ${fmt(a)}`); };
  assert.throws = (fn, esperado) => { try { fn(); } catch (e) { if (esperado instanceof RegExp && !esperado.test(e.message)) falhar(null, `o erro "${e.message}" não combina com ${esperado}`); return; } falhar(null, "esperava que lançasse um erro"); };

  self.onmessage = async (ev) => {
    const { arquivos, principal, modo } = ev.data;
    const testes = [], cache = {};
    const dir = (c) => (c.includes("/") ? c.slice(0, c.lastIndexOf("/")) : "");
    const normalizar = (c) => { const p = []; for (const s of c.split("/")) { if (!s || s === ".") continue; if (s === "..") p.pop(); else p.push(s); } return p.join("/"); };
    const registrar = (nome, fn) => { testes.push([nome, fn]); };
    function exigir(de, nome) {
      if (nome === "node:test" || nome === "test") {  // como no node: o próprio módulo é a função test, com test/it/describe de propriedades
        const t = (n, fn) => registrar(n, fn);
        return Object.assign(t, { test: t, it: t, describe: (n, f) => f() });
      }
      if (nome === "node:assert" || nome === "assert" || nome === "node:assert/strict") return assert;
      if (!nome.startsWith(".")) throw new Error(`módulo não encontrado: ${nome} (aqui só existem os arquivos do projeto)`);
      const base = normalizar(dir(de) + "/" + nome);
      const alvo = [base, base + ".js", base + "/index.js"].find((c) => c in arquivos);
      if (!alvo) throw new Error(`módulo não encontrado: ${nome}`);
      if (cache[alvo]) return cache[alvo].exports;
      const m = { exports: {} };
      cache[alvo] = m;
      new Function("module", "exports", "require", arquivos[alvo])(m, m.exports, (n) => exigir(alvo, n));
      return m.exports;
    }
    try {
      if (modo === "testar") {
        const alvos = Object.keys(arquivos).filter((c) => /(^|\/)(test[^/]*|[^/]*\.test|[^/]*_test)\.js$/.test(c));
        if (!alvos.length) { enviar("Nenhum arquivo de teste (o nome precisa ter \"test\", como calc.test.js)."); postMessage({ tipo: "fim", ok: false }); return; }
        for (const a of alvos) exigir("", "./" + a);
        let ok = 0, falhou = 0;
        for (const [nome, fn] of testes) {
          try { await fn(); enviar("✔ " + nome); ok++; } catch (e) { enviar("✖ " + nome + " — " + (e && e.message)); falhou++; }
        }
        enviar(`${ok} passaram, ${falhou} falharam`);
        postMessage({ tipo: "fim", ok: falhou === 0 && ok > 0 });
      } else {
        exigir("", "./" + principal);
        postMessage({ tipo: "fim", ok: true });
      }
    } catch (e) {
      enviar("[erro] " + (e && (e.stack || e.message)));
      postMessage({ tipo: "fim", ok: false });
    }
  };
}

export function trabalhadorPy() {
  const BASE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
  self.onmessage = async (ev) => {
    const { arquivos, principal, modo, harness } = ev.data;
    const enviar = (linha) => postMessage({ tipo: "saida", linha });
    try {
      enviar("(carregando o Python no navegador; só demora na primeira vez)");
      importScripts(BASE + "pyodide.js");
      const py = await loadPyodide({ indexURL: BASE, stdout: enviar, stderr: (l) => enviar("[erro] " + l) });  // eslint-disable-line no-undef
      py.FS.mkdirTree("/proj");
      for (const [c, t] of Object.entries(arquivos)) {
        py.FS.mkdirTree(c.includes("/") ? "/proj/" + c.slice(0, c.lastIndexOf("/")) : "/proj");
        py.FS.writeFile("/proj/" + c, t);
      }
      py.globals.set("PRINCIPAL", principal);
      if (modo === "testar") await py.runPythonAsync(harness);
      else await py.runPythonAsync("import runpy, sys, os\nos.chdir('/proj')\nsys.path.insert(0, '/proj')\nrunpy.run_path('/proj/' + PRINCIPAL, run_name='__main__')");
      postMessage({ tipo: "fim", ok: true });
    } catch (e) {
      enviar("[erro] " + (e && e.message ? e.message : e));
      postMessage({ tipo: "fim", ok: false });
    }
  };
}

// Roda as funções test_* dos arquivos test_*.py (parecido com o pytest, sem instalar nada).
export const HARNESS_PY = [
  "import sys, os, glob, traceback, importlib.util",
  "sys.path.insert(0, '/proj'); os.chdir('/proj')",
  "ok = falhou = 0",
  "alvos = sorted(set(glob.glob('/proj/**/test_*.py', recursive=True) + glob.glob('/proj/**/*_test.py', recursive=True)))",
  "if not alvos:",
  "    print('Nenhum arquivo de teste (o nome precisa começar com test_, como test_calc.py).')",
  "for caminho in alvos:",
  "    nome = os.path.splitext(os.path.basename(caminho))[0]",
  "    try:",
  "        spec = importlib.util.spec_from_file_location(nome, caminho); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)",
  "    except BaseException:",
  "        print('✖ erro ao carregar', nome); traceback.print_exc(); falhou += 1; continue",
  "    for f in sorted(dir(mod)):",
  "        if f.startswith('test_') and callable(getattr(mod, f)):",
  "            try:",
  "                getattr(mod, f)(); print('✔', nome + '::' + f); ok += 1",
  "            except BaseException as e:",
  "                print('✖', nome + '::' + f, '-', repr(e)[:200]); falhou += 1",
  "print(f'{ok} passaram, {falhou} falharam')",
].join("\n");

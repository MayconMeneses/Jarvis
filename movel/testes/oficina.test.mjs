// Oficina: ZIP conferido contra o zipfile do Python, e espaço de arquivos (projetos, limites, versões, desfazer).
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { ArmazemMemoria, Memoria } from "../js/memoria.js";
import { caminhoSeguro, EspacoOficina, MAX_ARQUIVOS, MAX_CHARS, MAX_VERSOES } from "../js/oficina-espaco.js";
import { crc32, zip } from "../js/zip.js";

const python = [process.env.PYTHON, "python", "python3"].filter(Boolean).find((p) => spawnSync(p, ["-c", "import zipfile"]).status === 0);

test("crc32 bate com o valor conhecido", () => assert.equal(crc32(new TextEncoder().encode("123456789")), 0xcbf43926));

test("zip é aceito pelo zipfile do Python, com nomes UTF-8, pastas e conteúdo intactos", { skip: !python && "Python não encontrado" }, () => {
  const arquivos = { "app/main.py": "print('olá, mundo')\n", "README.md": "# Título ✓\n", "vazio.txt": "", "pasta/sub/a.json": '{"x": 1}', "açaí.txt": "café" };
  const pasta = mkdtempSync(join(tmpdir(), "jarvis-zip-"));
  try {
    writeFileSync(join(pasta, "t.zip"), zip(arquivos, new Date(2026, 9, 20, 10, 30, 12)));
    const codigo = "import zipfile, json, sys; z = zipfile.ZipFile(sys.argv[1]); print(json.dumps({'ruim': z.testzip(), 'itens': {i.filename: z.read(i).decode('utf-8') for i in z.infolist()}, 'data': list(z.infolist()[0].date_time)}, ensure_ascii=False))";
    const r = spawnSync(python, ["-X", "utf8", "-c", codigo, join(pasta, "t.zip")], { encoding: "utf8" });
    assert.equal(r.status, 0, r.stderr);
    const saida = JSON.parse(r.stdout);
    assert.equal(saida.ruim, null);
    assert.deepEqual(saida.itens, arquivos);
    assert.deepEqual(saida.data, [2026, 10, 20, 10, 30, 12]);
  } finally { rmSync(pasta, { recursive: true, force: true }); }
});

const espaco = () => new EspacoOficina(new Memoria(new ArmazemMemoria()));

test("caminhoSeguro: relativo, até 4 níveis, só extensões de código/texto", () => {
  assert.equal(caminhoSeguro("a" + String.fromCharCode(92) + "b/c.py"), "a/b/c.py");
  assert.equal(caminhoSeguro(".gitignore"), ".gitignore");
  for (const ruim of ["/x.py", "C:/x.py", "../x.py", "a/../x.py", "a.exe", "a/b/c/d/e.py", "", ".env", "a b.py"]) assert.throws(() => caminhoSeguro(ruim), /não permitido/, ruim);
});

test("projetos: criar, salvar, listar e apagar arquivos", async () => {
  const e = espaco();
  assert.deepEqual(await e.projetos(), []);
  await e.salvar("Meu App", "src/main.py", "print(1)");
  await e.salvar("Meu App", "README.md", "# oi");
  assert.deepEqual(await e.projetos(), ["Meu App"]);
  assert.deepEqual(Object.keys(await e.arquivos("Meu App")), ["README.md", "src/main.py"]);
  assert.equal(await e.apagar("Meu App", "README.md"), true);
  assert.equal(await e.apagar("Meu App", "README.md"), false);
  assert.deepEqual(Object.keys(await e.arquivos("Meu App")), ["src/main.py"]);
  await assert.rejects(e.criar("../fora"), /nome de projeto inválido/);
  await assert.rejects(e.salvar("A", "x.py", "x".repeat(MAX_CHARS + 1)), /grande demais/);
});

test("limite de arquivos por projeto", async () => {
  const e = espaco();
  for (let i = 0; i < MAX_ARQUIVOS; i++) await e.salvar("P", `a${i}.py`, "x");
  await assert.rejects(e.salvar("P", "outro.py", "x"), /arquivos demais/);
  await e.salvar("P", "a0.py", "y");  // reescrever um existente continua valendo
});

test("versões e desfazer: guarda as últimas 20, desfazer de novo refaz, apagar também desfaz", async () => {
  const e = espaco();
  await e.salvar("P", "a.py", "v1");
  await e.salvar("P", "a.py", "v1");  // igual: não cria versão
  assert.equal(await e.versoes("P", "a.py"), 0);
  await e.salvar("P", "a.py", "v2");
  await e.salvar("P", "a.py", "v3");
  assert.equal(await e.versoes("P", "a.py"), 2);
  assert.equal(await e.desfazer("P", "a.py"), "v2");
  assert.equal((await e.arquivos("P"))["a.py"], "v2");
  assert.equal(await e.desfazer("P", "a.py"), "v3");  // a versão atual virou histórico: desfazer de novo refaz
  assert.equal(await e.desfazer("P", "a.py"), "v2");
  await e.apagar("P", "a.py");
  assert.deepEqual(await e.arquivos("P"), {});
  await e.salvar("P", "a.py", "novo");
  assert.ok(await e.versoes("P", "a.py") >= 1);
  await assert.rejects(e.desfazer("P", "nunca.py"), /não há versão/);
  for (let i = 0; i < MAX_VERSOES + 5; i++) await e.salvar("P", "b.py", `v${i}`);
  assert.equal(await e.versoes("P", "b.py"), MAX_VERSOES);
});

test("os arquivos da Oficina entram na cópia de segurança da memória", async () => {
  const memoria = new Memoria(new ArmazemMemoria());
  await new EspacoOficina(memoria).salvar("P", "a.py", "print(1)");
  assert.match(await memoria.exportar(), /Oficina\/P\/a\.py/);
});

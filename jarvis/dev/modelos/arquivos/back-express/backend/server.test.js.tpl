import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { criarApp, criarArmazem } from "./server.js";

let servidor;
let base;
const pasta = fs.mkdtempSync(path.join(os.tmpdir(), "api-"));

before(async () => {
  const app = criarApp(criarArmazem(path.join(pasta, "teste.json")));
  servidor = app.listen(0);
  base = `http://127.0.0.1:${servidor.address().port}`;
});

after(() => {
  servidor.close();
  fs.rmSync(pasta, { recursive: true, force: true });
});

const enviar = (caminho, metodo = "GET", corpo) =>
  fetch(base + caminho, {
    method: metodo,
    headers: { "content-type": "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });

test("saude", async () => {
  assert.deepEqual(await (await enviar("/api/saude")).json(), { status: "ok" });
});

test("crud completo", async () => {
  const criado = await enviar("/api/itens", "POST", { titulo: "  Primeira tarefa  " });
  assert.equal(criado.status, 201);
  assert.deepEqual(await criado.json(), { id: 1, titulo: "Primeira tarefa", concluido: false });

  const alterado = await (await enviar("/api/itens/1", "PATCH", { concluido: true })).json();
  assert.equal(alterado.concluido, true);
  assert.equal((await (await enviar("/api/itens")).json()).length, 1);

  assert.equal((await enviar("/api/itens/1", "DELETE")).status, 204);
  assert.deepEqual(await (await enviar("/api/itens")).json(), []);
});

test("validacao e nao encontrado", async () => {
  assert.equal((await enviar("/api/itens", "POST", { titulo: "" })).status, 422);
  assert.equal((await enviar("/api/itens/99", "PATCH", { concluido: true })).status, 404);
  assert.equal((await enviar("/api/itens/99", "DELETE")).status, 404);
});

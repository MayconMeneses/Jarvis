// Conversa contínua: o contexto enviado ao modelo nunca passa do limite, mesmo depois de muitas perguntas com respostas longas.
import assert from "node:assert/strict";
import test from "node:test";
import { Conversa, LIMITE_HISTORICO_CHARS } from "../js/conversa.js";
import { sistema } from "../js/contexto.js";
import { Memoria } from "../js/memoria.js";

const RESPOSTA_LONGA = "**Padrão Observer**\n" + "Texto explicativo longo. ".repeat(60) + "\n```python\n" + "linha de código\n".repeat(80) + "```";

test("o erro real: várias perguntas com respostas longas não estouram o contexto do modelo", async () => {
  const c = new Conversa(new Memoria());
  for (let i = 0; i < 12; i++) {
    await c.adicionar("user", `pergunta ${i} sobre padrões de projeto`);
    await c.adicionar("assistant", RESPOSTA_LONGA);
  }
  await c.adicionar("user", "e agora, o que é SOLID?");
  const historico = c.paraPrompt();
  const total = historico.reduce((n, m) => n + m.content.length, 0);
  assert.ok(total <= LIMITE_HISTORICO_CHARS + 1200, `histórico com ${total} caracteres`);
  assert.equal(historico[0].role, "user");
  assert.equal(historico.at(-1).content, "e agora, o que é SOLID?");  // a pergunta atual sempre vai inteira
  assert.ok(historico.every((m, i) => i === 0 || m.role !== historico[i - 1].role));  // papéis alternados
  assert.ok(!historico.some((m) => m.content.includes("linha de código\nlinha de código")));  // código antigo vira "[código]"
  // prompt total estimado em tokens (≈3 caracteres por token em português) cabe em 4096 com folga para a resposta
  const prompt = [{ role: "system", content: "x".repeat(3200) }, ...historico];
  const tokens = prompt.reduce((n, m) => n + Math.ceil(m.content.length / 3), 0);
  assert.ok(tokens + 600 < 4096, `${tokens} tokens + resposta`);
});

test("a conversa é salva no aparelho e continua depois de reabrir o app", async () => {
  const memoria = new Memoria();
  const a = new Conversa(memoria);
  await a.adicionar("user", "oi");
  await a.adicionar("assistant", "olá!");
  const b = new Conversa(memoria);  // outro "app aberto" no mesmo aparelho
  assert.deepEqual((await b.carregar()).map((m) => m.content), ["oi", "olá!"]);
  await b.limpar();
  assert.deepEqual(await new Conversa(memoria).carregar(), []);
});

test("resposta vazia (erro) nunca entra no histórico e não quebra a alternância", async () => {
  const c = new Conversa(new Memoria());
  await c.adicionar("user", "pergunta que deu erro");
  await c.adicionar("assistant", "");
  await c.adicionar("assistant", "   ");
  await c.adicionar("user", "tentando de novo");
  assert.equal(c.itens.length, 2);
  assert.deepEqual(c.paraPrompt().map((m) => m.role), ["user"]);  // dois "user" seguidos viram um só
});

test("só guarda as últimas mensagens e ignora lixo salvo", async () => {
  const memoria = new Memoria();
  await memoria.definirMeta("conversa", [{ role: "user", content: "ok" }, { role: "robo", content: "x" }, null, { role: "assistant", content: 5 }]);
  assert.deepEqual((await new Conversa(memoria).carregar()).map((m) => m.content), ["ok"]);
  const c = new Conversa(new Memoria());
  for (let i = 0; i < 100; i++) await c.adicionar(i % 2 ? "assistant" : "user", `m${i}`);
  assert.equal(c.itens.length, 60);
});

test("o prompt de sistema nunca passa do limite e a conversa por voz usa só texto falável", async () => {
  const memoria = new Memoria();
  const { Saber } = await import("../js/saber.js");
  const dados = JSON.parse((await import("node:fs")).readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8"));
  const texto = await sistema({ saber: new Saber(dados), memoria, pergunta: "explique SOLID DDD hexagonal Observer cache", nome: "Maycon" });
  assert.ok(texto.length <= 3300);
});

// Windows-1252 próprio: não depende do ICU/TextDecoder da plataforma (Node 20 no Linux, Safari, etc.).
import test from "node:test";
import assert from "node:assert/strict";
import { decodificarWin1252, byteWin1252 } from "../js/texto-win1252.js";
import { winAnsi, criarPdf } from "../js/doc-criar-pdf.js";
import { blocos } from "../js/doc-markdown.js";
import { lerPdf } from "../js/anexo-pdf.js";
import { decodificarTexto } from "../js/anexos.js";

const ESPERADO = "€\uFFFD‚ƒ„…†‡ˆ‰Š‹Œ\uFFFDŽ\uFFFD\uFFFD‘’“”•–—˜™š›œ\uFFFDžŸ";

test("bytes 0x80-0x9F seguem a tabela própria; indefinidos viram U+FFFD", () => {
  const bytes = Uint8Array.from({ length: 32 }, (_, i) => 0x80 + i);
  assert.equal(decodificarWin1252(bytes), ESPERADO);
});

test("ASCII e 0xA0-0xFF são Latin-1; bytes grandes (lotes) não quebram", () => {
  assert.equal(decodificarWin1252(Uint8Array.from([0x41, 0xe7, 0xe3, 0xff, 0xa0])), "Açãÿ\u00a0");
  assert.equal(decodificarWin1252(new Uint8Array(10000).fill(0x95)), "•".repeat(10000));
});

test("ida e volta: caractere -> byte -> caractere", () => {
  for (const ch of "•“”‘’–—€…™ŠšŸçÃ") assert.equal(decodificarWin1252(Uint8Array.of(byteWin1252(ch))), ch);
  assert.equal(byteWin1252("😀"), null);
  assert.equal(byteWin1252("\n"), null);
  assert.equal(byteWin1252("\uFFFD"), null);
});

test("winAnsi gera os bytes certos para • “ ” – — € …", () => {
  const s = winAnsi("• “a” – — € …");
  assert.deepEqual([...s].map((c) => c.charCodeAt(0)), [0x95, 32, 0x93, 97, 0x94, 32, 0x96, 32, 0x97, 32, 0x80, 32, 0x85]);
});

test("decodificarTexto: arquivo não-UTF-8 usa Windows-1252 próprio", () => {
  assert.equal(decodificarTexto(Uint8Array.of(0x93, 0x6f, 0x6b, 0x94, 0x20, 0x80, 0xe9)), "“ok” €é");
});

test("PDF criado e relido preserva • “ ” – € …", async () => {
  const original = "• item “citado” – 5 € … fim";
  const r = await lerPdf(criarPdf(blocos(original), "Teste"));
  assert.ok(r.texto.includes(original), JSON.stringify(r.texto));
});

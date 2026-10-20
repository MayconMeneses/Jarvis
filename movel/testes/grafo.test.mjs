// Grafo do Second Brain: áreas pelo prefixo, nós/ligações, limite de 150, posições, toque e segurança (XSS).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { AREAS, areaDaNota, construirGrafo, noEm, posicionar, raioDoNo } from "../js/areas.js";
import { cortarRotulo, desenharGrafo } from "../js/grafo-desenho.js";

const nota = (ref, corpo = "", titulo) => ({ ref, titulo: titulo || ref.split("/").pop(), corpo, atualizada: "2026-01-01" });

test("8 áreas com as cores fixas", () => {
  assert.deepEqual(AREAS.map((a) => [a.id, a.cor]), [["metas", "#fbbf24"], ["trabalho", "#ff5547"], ["projetos", "#8b7cff"], ["financas", "#f7931a"],
    ["aprendizado", "#2dd4ff"], ["saude", "#10b981"], ["relacoes", "#ec4899"], ["meta", "#8a90a6"]]);
});

test("área vem do prefixo do nome (sem acento); o que não conhece cai em meta", () => {
  const casos = {
    "Projetos/Loja/Sobre": "projetos", "Oficina/app/main.py": "projetos", "Lembranças/gosto de café": "meta", "Diário/2026-01-01": "meta",
    "Aprendizado/rust": "aprendizado", "Finanças/Meta": "financas", "Saúde/Dormir": "saude", "Relações/Ana": "relacoes", "Metas/Correr": "metas",
    "Perfil/Dev": "trabalho", "Trabalho/X": "trabalho", "Lembretes/2026": "metas", "Qualquer coisa": "meta", "": "meta", "constructor/x": "meta", "__proto__/x": "meta",
  };
  for (const [ref, area] of Object.entries(casos)) assert.equal(areaDaNota(ref), area, ref);
});

test("grafo: núcleo, 8 áreas, uma nota por nó, links [[nota]] e tamanho por ligações", () => {
  const g = construirGrafo([nota("Projetos/A", "veja [[Projetos/B]] e [[b]] e [[inexistente]]"), nota("Projetos/B", "volta [[A]]"), nota("Metas/C")]);
  assert.equal(g.nos.filter((n) => n.tipo === "nota").length, 3);
  assert.equal(g.nos.filter((n) => n.tipo === "area").length, 8);
  assert.equal(g.arestas.filter((e) => e.link).length, 1, "A<->B conta uma vez só");
  const a = g.porId.get("n:Projetos/A"), c = g.porId.get("n:Metas/C");
  assert.equal(a.grau, 2);  // área + link
  assert.equal(c.grau, 1);
  assert.ok(raioDoNo(a) > raioDoNo(c));
  assert.ok(raioDoNo(g.nos[0]) > raioDoNo(g.porId.get("a:metas")));
});

test("no máximo 150 notas, repartidas entre as áreas (a Oficina não engole as outras)", () => {
  const notas = [...Array.from({ length: 300 }, (_, i) => nota(`Oficina/p/arq${i}.js`)), ...Array.from({ length: 5 }, (_, i) => nota(`Saúde/n${i}`))];
  const g = construirGrafo(notas);
  assert.equal(g.nos.filter((n) => n.tipo === "nota").length, 150);
  assert.equal(g.nos.filter((n) => n.area === "saude" && n.tipo === "nota").length, 5);
  assert.equal(g.total, 305);
});

test("posições: dentro da tela, sem nós empilhados, toque acha o nó certo", () => {
  const g = construirGrafo(Array.from({ length: 60 }, (_, i) => nota(`Aprendizado/t${i}`)));
  const pos = posicionar(g, 390, 360);
  for (const p of pos.values()) assert.ok(p.x >= 12 && p.x <= 378 && p.y >= 12 && p.y <= 348);
  const lista = g.nos.filter((n) => n.tipo === "nota");
  let colados = 0;
  for (let i = 0; i < lista.length; i++) for (let j = i + 1; j < lista.length; j++) {
    const a = pos.get(lista[i].id), b = pos.get(lista[j].id);
    if (Math.hypot(a.x - b.x, a.y - b.y) < 2) colados++;
  }
  assert.equal(colados, 0);
  const alvo = lista[7], p = pos.get(alvo.id);
  assert.equal(noEm(g, pos, p.x + 1, p.y + 1)?.id, alvo.id);
  assert.equal(noEm(g, pos, -50, -50), null);
});

class Ctx {
  constructor() { this.textos = []; this.chamadas = 0; }
  createRadialGradient() { return { addColorStop() {} }; }
  fillText(t) { this.textos.push(t); }
}
const ctxFalso = () => new Proxy(new Ctx(), { get: (o, k) => (k in o ? o[k] : () => { o.chamadas++; }), set: () => true });

test("XSS: título com <img onerror> só vira texto no canvas, e nenhum módulo usa innerHTML", () => {
  const mau = "<img src=x onerror=alert(1)>";
  const g = construirGrafo([nota("Projetos/" + mau, "", mau)]);
  const pos = posicionar(g, 390, 360), ctx = ctxFalso();
  desenharGrafo(ctx, g, pos, 390, 360, { t: 0, pulsos: [{ aresta: 3, u: 0.5 }], selecionado: "n:Projetos/" + mau, animar: true });
  assert.ok(ctx.textos.some((t) => t.includes("<img")), "o título aparece como texto desenhado");
  assert.ok(ctx.chamadas > 20);
  for (const arq of ["areas", "grafo-desenho", "painel-grafo", "cartao-memoria", "orbe-ui", "painel-memoria"]) {
    const src = readFileSync(new URL(`../js/${arq}.js`, import.meta.url), "utf8");
    assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(src), arq);
  }
});

test("rótulos longos são cortados", () => { assert.ok(cortarRotulo("x".repeat(80)).length <= 26); });

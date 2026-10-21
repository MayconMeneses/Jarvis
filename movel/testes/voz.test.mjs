// Fala em pt-BR: o celular tem que falar como o PC. Os casos vêm de testes/dados/casos_python.json, gerado pela SAÍDA REAL do Python
// (jarvis/voice, jarvis/radar/numeros_pt, jarvis/info/leitor); tests/test_normalizar_compartilhado.py confere que o arquivo continua igual ao Python.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { detectar } from "../js/leitor-idioma.js";
import { partes, resumir } from "../js/leitor-partes.js";
import { falarTexto } from "../js/radar-numeros.js";
import { normalizar } from "../js/voz-normalizar.js";
import { ordinal, porExtenso } from "../js/voz-numeros.js";
import { MAX_FALADO, dividirParaFala, limparParaFala, pausaMs } from "../js/voz-texto.js";

const casos = JSON.parse(readFileSync(new URL("./dados/casos_python.json", import.meta.url), "utf8"));
const confere = (nome, fn, lista) => test(`paridade com o Python: ${nome} (${lista.length} casos)`, () => { for (const [entrada, esperado] of lista) assert.deepEqual(fn(entrada), esperado, JSON.stringify(entrada)); });

confere("normalizar (números, horas, datas, moedas, siglas, unidades)", normalizar, casos.normalizar);
confere("números por extenso", porExtenso, casos.por_extenso);
confere("texto do boletim (numeros_pt.falar_texto)", falarTexto, casos.falar_radar);
confere("limpar para a fala", limparParaFala, casos.limpar_para_fala);
confere("dividir para a fala", dividirParaFala, casos.dividir_para_fala);
confere("detecção de idioma", detectar, casos.idioma);
confere("partes de até 350 caracteres", (t) => partes(t), casos.partes);

test("feminino, ordinais e entradas vazias", () => {
  assert.equal(porExtenso(2, true), "duas");
  assert.equal(porExtenso(201, true), "duzentas e uma");
  assert.equal(ordinal(1), "primeiro");
  assert.equal(ordinal(2, true), "segunda");
  assert.equal(ordinal(15), "quinze");
  assert.deepEqual(dividirParaFala("Oi."), ["Oi."]);
  assert.deepEqual(dividirParaFala(""), []);
});

test("marcação, links, emojis, listas e código não chegam à voz", () => {
  const falado = limparParaFala("# Título\n- primeiro item\n- segundo item\n1. passo um\n**negrito** e _itálico_ 🙂🚀\nveja [o site](https://exemplo.com/a?b=1) ou https://x.org e escreva a fulano@exemplo.com\n```py\nprint(1)\n```\narquivo C:\\Users\\a\\b.txt");
  for (const lixo of ["#", "*", "_", "http", "@", "🙂", "🚀", "print", "[", "]", "```", "\\"]) assert.ok(!falado.includes(lixo), lixo);
  assert.match(falado, /o site/);
  assert.match(falado, /código na janela/);
  assert.match(falado, /um endereço de i-meio/);
  assert.match(falado, /Título\. primeiro item\. segundo item\. passo um\./);
});

test("texto longo é cortado e só depois normalizado; normalizar é idempotente e não deixa dígitos", () => {
  const falado = limparParaFala("A RAM está em 95% agora. ".repeat(80));
  assert.ok(falado.endsWith("Os detalhes estão na janela.") && !/\d/.test(falado));
  assert.ok(limparParaFala("Esta é uma frase de teste. ".repeat(60)).length <= MAX_FALADO + 40);
  for (const frase of ["São 14:30 do dia 20/10/2026, R$ 1.234,56 (12,5%)", "RAM 8 GB, CPU 45%, 3 e-mails", "Dr. Silva 1º lugar"]) {
    const uma = normalizar(frase);
    assert.ok(!/\d/.test(uma) && normalizar(uma) === uma, frase);
  }
});

test("entradas estranhas nunca levantam erro (300 sorteios com semente fixa + casos extremos)", () => {
  let semente = 7;
  const sorteio = () => (semente = (semente * 1103515245 + 12345) % 2147483648) / 2147483648;
  const alfabeto = [..."abcXYZ 0123456789.,;:!?-_*#<>[](){}\n\t\\/%$@&+=ãéçº°ª€→…🙂\u200d\ufe0f"];
  for (let i = 0; i < 300; i++) {
    const lixo = Array.from({ length: Math.floor(sorteio() * 80) }, () => alfabeto[Math.floor(sorteio() * alfabeto.length)]).join("");
    assert.equal(typeof limparParaFala(lixo), "string");
    assert.equal(typeof falarTexto(lixo), "string");
  }
  for (const caso of ["", "   ", "\n\n", "99999999999999999999999999 reais", "R$ " + "9".repeat(40), "0".repeat(50), "..,,;;", "1/0 e 0/1 e 32/13", "9".repeat(5000)]) {
    assert.equal(typeof limparParaFala(caso), "string");
    assert.equal(typeof falarTexto(caso), "string");
  }
});

test("pausas: ponto e interrogação respiram mais que vírgula; a 1ª parte sai curta", () => {
  assert.ok(pausaMs("Fim.") > pausaMs("segue,") && pausaMs("Certo?") >= pausaMs("Fim."));
  const longa = "Claro, Maycon, vou olhar isso agora mesmo e te conto tudo que encontrar na sua agenda de hoje, incluindo as reuniões. Depois eu aviso.";
  const p = dividirParaFala(longa);
  assert.ok(p[0].length <= 60 && p.length === 3);
});

test("resumo barato do leitor corta em fim de frase", () => {
  const texto = "Primeira frase longa o bastante para contar. ".repeat(40);
  const r = resumir(texto, 300);
  assert.ok(r.length <= 300 && r.endsWith("."));
  assert.equal(resumir("curto"), "curto");
});

test("os arquivos de voz não usam innerHTML e cada um tem no máximo 300 linhas", () => {
  for (const arq of ["voz-numeros", "voz-normalizar", "voz-texto", "radar-numeros", "leitor-partes", "leitor-idioma"]) {
    const src = readFileSync(new URL(`../js/${arq}.js`, import.meta.url), "utf8");
    assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(src), arq);
    assert.ok(src.split("\n").length <= 300, arq);
  }
});

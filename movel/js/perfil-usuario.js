// Perfil do usuário no celular (porte de jarvis/conversa/perfil.py): quem sou, projetos, preferências, tom e metas. Lógica pura sobre a Memoria
// (IndexedDB do app). Fica na nota "Perfil do Usuário". O que o usuário não definiu é DEDUZIDO das notas; o definido sempre vence.
// Quem grava é o painel, só depois do "Aprovar" (aprovar aqui valida de novo). Dado sensível é recusado.
import { fold } from "./util.js";

export const REF = "Perfil do Usuário";
export const CAMPOS = { quem: "Quem sou", projetos: "Projetos", preferencias: "Preferências", tom: "Tom de conversa", metas: "Metas" };
export const MAX_VALOR = 300;
const CONTROLE = /[\x00-\x1f\x7f]|\[\[|\]\]/;
const LINHA = /^-\s*([^:]{2,30}):\s*(.+)$/;
// Senha, documento, dinheiro, saúde e chaves: nunca viram perfil (mesma regra do PC, sobre o texto sem acento).
const SENSIVEL = /\b(senha|password|cpf|rg|cartao|cvv|token|chave de api|api key|pix|saldo|salario|fatura|conta bancaria|diagnostico|remedio|doenca)\b|r\$\s*\d|\b\d[\d.,]*\s*(reais|mil reais)\b/;
const MASCARAS = [/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/, /\b(?:\d[ -]?){13,19}\b/, /[\w.+-]+@[\w-]+\.[\w.-]+/, /(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b/,
  /\b(?:sk-|AIza|nvapi-|ghp_|xox[bp]-)[\w-]{10,}/, /\b[A-Za-z0-9_-]{40,}\b/];

export const sensivel = (texto) => SENSIVEL.test(fold(texto)) || MASCARAS.some((m) => m.test(String(texto)));

// Devolve { campo, valor } limpo ou lança Error com a razão (em português, para mostrar ao usuário).
export function validar(campo, valor) {
  if (!Object.hasOwn(CAMPOS, campo)) throw new Error(`campo desconhecido (use: ${Object.values(CAMPOS).join(", ")})`);
  valor = String(valor ?? "").replace(/\s+/g, " ").trim();
  if (!valor || valor.length > MAX_VALOR) throw new Error(`o valor precisa ter de 1 a ${MAX_VALOR} caracteres`);
  if (CONTROLE.test(valor)) throw new Error("valor com caracteres não permitidos");
  if (sensivel(valor)) throw new Error("isso parece dado sensível (senha, documento, valor em dinheiro ou saúde); não guardo no perfil");
  return { campo, valor };
}

export async function definidos(memoria) {
  const achados = {}, porNome = Object.fromEntries(Object.entries(CAMPOS).map(([k, v]) => [v, k]));
  for (const linha of ((await memoria.ler(REF))?.corpo || "").split("\n")) {
    const m = LINHA.exec(linha.trim());
    if (m && porNome[m[1].trim()]) achados[porNome[m[1].trim()]] = m[2].trim().slice(0, MAX_VALOR);
  }
  return achados;
}

const nomesDe = async (memoria, prefixo, max) => [...new Set((await memoria.listar(prefixo)).map((n) => n.ref.split("/")[1]).filter(Boolean))].slice(0, max);

export async function deduzidos(memoria) {
  const valores = {}, quem = [], nome = await memoria.meta("nome");
  if (nome) quem.push(String(nome));
  const dev = (await memoria.ler("Perfil/Dev"))?.corpo || "";
  const pega = (k) => new RegExp(`^${k}:\\s*(.+)$`, "m").exec(dev)?.[1].trim();
  if (pega("cidade")) quem.push(`mora em ${pega("cidade")}`);
  if (pega("stack")) quem.push(`stack ${pega("stack")}`);
  if (pega("nivel")) quem.push(`nível ${pega("nivel")}`);
  if (quem.length) valores.quem = quem.join(", ").slice(0, MAX_VALOR);
  const projetos = await nomesDe(memoria, "Projetos/", 8), metas = await nomesDe(memoria, "Metas/", 5);
  if (projetos.length) valores.projetos = projetos.join(", ").slice(0, MAX_VALOR);
  if (metas.length) valores.metas = metas.join("; ").slice(0, MAX_VALOR);
  return valores;
}

// campo -> { valor, origem: "definido" | "deduzido" }
export async function compilar(memoria) {
  const saida = {};
  for (const [c, v] of Object.entries(await deduzidos(memoria))) saida[c] = { valor: v, origem: "deduzido" };
  for (const [c, v] of Object.entries(await definidos(memoria))) saida[c] = { valor: v, origem: "definido" };
  return saida;
}

export async function paraPrompt(memoria, limite = 500) {
  const p = await compilar(memoria);
  return Object.keys(CAMPOS).filter((c) => p[c]).map((c) => `- ${CAMPOS[c]}: ${p[c].valor}`).join("\n").slice(0, limite);
}

// Texto do cartão de aprovação: o que muda e o que havia antes. Não grava nada.
export async function proposta(memoria, campo, valor) {
  const apagar = String(valor ?? "").trim() === "", atual = await definidos(memoria);
  if (apagar) {
    if (!Object.hasOwn(CAMPOS, campo)) throw new Error("campo desconhecido");
    if (!atual[campo]) throw new Error("esse campo não está definido no seu perfil");
    return { campo, valor: "", texto: `Apagar do seu perfil: ${CAMPOS[campo]} (hoje: ${atual[campo]})` };
  }
  const v = validar(campo, valor);
  return { ...v, texto: `Atualizar seu perfil? ${CAMPOS[campo]}: ${v.valor}` + (atual[campo] ? `\n(antes: ${atual[campo]})` : "") };
}

// Só chamar depois do Aprovar. Valor vazio apaga o campo.
export async function aprovar(memoria, campo, valor) {
  const atual = await definidos(memoria), apagar = String(valor ?? "").trim() === "";
  if (apagar) { if (!Object.hasOwn(CAMPOS, campo)) throw new Error("campo desconhecido"); delete atual[campo]; } else atual[campo] = validar(campo, valor).valor;
  const corpo = "# Perfil do Usuário\n\n" + Object.keys(CAMPOS).filter((c) => atual[c]).map((c) => `- ${CAMPOS[c]}: ${atual[c]}`).join("\n") + "\n";
  await memoria.guardar(REF, corpo, "perfil", "Perfil do usuário (definido por ele)");
  return apagar ? `Apaguei “${CAMPOS[campo]}” do seu perfil.` : `Perfil atualizado: ${CAMPOS[campo]} = ${atual[campo]}.`;
}

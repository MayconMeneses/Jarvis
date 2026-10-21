// Catálogo curado de fontes por nicho (dados/radar-fontes.json, cópia de jarvis/radar/dados/fontes_base.json). Porte de jarvis/radar/catalogo.py.
// A IA nunca "aprova" fonte: só entra o que está no catálogo.
import { palavras as palavrasDe } from "./radar-dedup.js";
import { semAcento } from "./radar-texto.js";

// Fontes do catálogo cujo assunto aparece no nicho (ex.: "IA aplicada a saúde" -> ia). Sempre inclui as gerais.
export function sugerir(nicho, catalogo, limite = 12) {
  const texto = ` ${semAcento(nicho)} `, palavras = texto.split(/\s+/);
  const achadas = catalogo.filter((f) => f.nichos.some((n) => texto.includes(` ${n} `) || palavras.includes(n)));
  const gerais = catalogo.filter((f) => f.nichos.includes("geral") && !achadas.includes(f));
  return [...achadas, ...gerais].slice(0, limite).map((f) => ({ nome: f.nome, url: f.feed, nota: Number(f.curada) || 5, tipo: f.tipo, idioma: f.idioma }));
}

// Palavras-chave do nicho para a relevância: as palavras com sentido (3+ letras) e "ia" como caso especial.
export function palavrasChave(nicho) {
  const chaves = palavrasDe(nicho);
  if (/(^|\s)ia(\s|$)/.test(semAcento(nicho))) chaves.push("inteligencia artificial");
  return [...new Set(chaves)];
}

export async function carregarCatalogo(buscar = (...a) => fetch(...a), url = "dados/radar-fontes.json") {
  const r = await buscar(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const dados = await r.json();
  if (!Array.isArray(dados)) throw new Error("catálogo inválido");
  return dados.filter((f) => f && typeof f.nome === "string" && typeof f.feed === "string" && Array.isArray(f.nichos));
}

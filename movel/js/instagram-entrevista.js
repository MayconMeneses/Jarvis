// Entrevista curta do analista de Instagram no celular (igual a jarvis/instagram/entrevista.py): sem estado escondido,
// cada resposta ("campo: valor") é gravada e o que falta é recalculado a cada vez.
import { PESOS_PADRAO, normalizarPerfil, numero } from "./instagram-base.js";
import { fold } from "./util.js";

export const CAMPOS = [
  ["nicho", "nicho (ex.: nutrição esportiva)"], ["proprio", "o seu @ (ex.: meu perfil: @voce)"],
  ["concorrentes", "5 a 15 concorrentes com seguidores (ex.: concorrentes: @a (12,3 mil), @b (8 mil))"], ["objetivo", "objetivo (ex.: objetivo: vender mentoria)"],
  ["vitoria", "como mede vitória (ex.: vitória: 500 novos seguidores por mês)"], ["pesos", ""], ["formatos", "formatos que posta (ex.: formatos: reels, carrossel)"],
  ["frequencia", ""], ["temas_suspeitos", ""], ["origem", ""],
];
const OPCIONAIS = new Set(["pesos", "temas_suspeitos", "frequencia", "origem"]);
const ALIAS = { nicho: "nicho", "meu perfil": "proprio", perfil: "proprio", arroba: "proprio", "meu arroba": "proprio", proprio: "proprio", concorrentes: "concorrentes",
  objetivo: "objetivo", vitoria: "vitoria", "definicao de vitoria": "vitoria", pesos: "pesos", formatos: "formatos", frequencia: "frequencia",
  "temas suspeitos": "temas_suspeitos", temas: "temas_suspeitos", dados: "origem", "origem dos dados": "origem", fonte: "origem" };

export function separarRespostas(texto) {
  const achados = [...texto.matchAll(/(?:^|[\n;])\s*([a-zA-ZÀ-ÿ ]{3,25}?)\s*:\s*/gm)], respostas = {};
  achados.forEach((m, i) => {
    const fim = i + 1 < achados.length ? achados[i + 1].index : texto.length;
    const campo = ALIAS[fold(m[1]).trim()];
    if (campo) respostas[campo] = texto.slice(m.index + m[0].length, fim).replace(/^[ ;\n]+|[ ;\n]+$/g, "").slice(0, 600);
  });
  return respostas;
}

export function parsePesos(texto) {
  const pesos = { ...PESOS_PADRAO };
  for (const [, nome, valor] of fold(texto).matchAll(/(salvamentos?|compartilhamentos?|coment\w+|likes?|curtidas?)\s*(?:=|:|x)?\s*(\d+(?:[.,]\d+)?)/g)) {
    const campo = nome.startsWith("salv") ? "salvamentos" : nome.startsWith("compart") ? "compartilhamentos" : nome.startsWith("coment") ? "comentarios" : "likes";
    pesos[campo] = Number(valor.replace(",", "."));
  }
  const igual = Object.keys(pesos).every((k) => pesos[k] === PESOS_PADRAO[k]);
  if (texto.trim() && igual && !/padrao|\d/.test(fold(texto))) throw new Error("não entendi os pesos (use: salvamentos 3, compartilhamentos 3, comentários 2, likes 1)");
  return pesos;
}

export function parseConcorrentes(texto) {
  const saida = {};
  for (const parte of texto.split(/,(?![^()]*\))|;/)) {
    const m = /^\s*(@?[\w.]{1,30})\s*(?:\(([^)]*)\))?/.exec(parte), arroba = m ? normalizarPerfil(m[1]) : "";
    if (m && arroba && /[a-z]/.test(arroba)) saida[arroba] = numero((m[2] || "").replace(/\s*seguidores?/i, ""));
  }
  return saida;
}

export function aplicar(texto, atual = {}) {
  const perfil = { ...atual }, avisos = [];
  for (const [campo, valor] of Object.entries(separarRespostas(texto))) {
    try {
      if (campo === "pesos") perfil.pesos = parsePesos(valor);
      else if (campo === "proprio") perfil.proprio = normalizarPerfil(valor.split(/\s+/)[0] || "");
      else if (campo === "concorrentes") {
        perfil.concorrentes = parseConcorrentes(valor);
        const n = Object.keys(perfil.concorrentes).length;
        if (n < 5 || n > 15) avisos.push(`Você citou ${n} concorrentes; o ideal são 5 a 15 (segue assim mesmo).`);
      } else perfil[campo] = valor;
    } catch (e) { avisos.push(e.message); }
  }
  const faltam = CAMPOS.filter(([campo]) => !OPCIONAIS.has(campo) && !perfil[campo] ).map(([, pergunta]) => pergunta);
  return [perfil, faltam, avisos];
}

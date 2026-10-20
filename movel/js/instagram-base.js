// Analista de Instagram no celular, parte 1: números, datas, higiene e ganchos. Mesma lógica do PC (jarvis/instagram/*.py);
// os casos compartilhados estão em tests/dados/instagram_casos.json (lidos pelo pytest e pelo node:test).
import { fold } from "./util.js";

export const PESOS_PADRAO = { salvamentos: 3, compartilhamentos: 3, comentarios: 2, likes: 1 };
export const HORAS_MADURO = 48, MIN_POSTS_PERFIL = 6, MIN_POSTS_GRUPO = 3, LIMITE_OUTLIER = 2.0, LIMITE_COMENTARIO_PCT = 30, MAX_LEGENDA = 200;
export const CAMPOS_NUMERICOS = ["likes", "comentarios", "views", "salvamentos", "compartilhamentos"];

const VAZIOS = new Set(["", "-", "--", "n/d", "nd", "na", "n/a", "oculto", "ocultos", "hidden", "null", "none", "nan", "?"]);
const MULT = { mil: 1e3, k: 1e3, mi: 1e6, m: 1e6, milhao: 1e6, milhoes: 1e6 };

export function numero(valor) {
  if (valor == null || typeof valor === "boolean") return null;
  if (typeof valor === "number") return valor >= 0 ? Math.floor(valor + 0.5) : null;
  const texto = fold(valor).trim();
  if (VAZIOS.has(texto)) return null;
  const achado = /^([\d.,]+)\s*(mil|mi|milhao|milhoes|k|m)?$/.exec(texto);
  if (!achado) return null;
  const [, digitos, sufixo] = achado;
  if (sufixo) {
    let decimal = digitos.replace(/,/g, ".");
    if (decimal.split(".").length > 2) { const partes = decimal.split("."); decimal = partes.slice(0, -1).join("") + "." + partes.at(-1); }
    const n = Number(decimal);
    return Number.isNaN(n) ? null : Math.floor(n * MULT[sufixo] + 0.5);
  }
  if (/^\d{1,3}([.,]\d{3})+$/.test(digitos)) return Number(digitos.replace(/[.,]/g, ""));
  return /^\d+$/.test(digitos) ? Number(digitos) : null;
}

const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?$/;
const BR = /^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:[ T,]+(\d{1,2})[:h](\d{2}))?$/;

// Segundos UTC de uma data ISO ou brasileira (sem fuso = UTC). Data impossível = null.
export function epoch(texto) {
  const t = String(texto ?? "").trim();
  let ano, mes, dia, hora, minuto, seg, fuso;
  let m = ISO.exec(t);
  if (m) [, ano, mes, dia, hora, minuto, seg, fuso] = m;
  else if ((m = BR.exec(t))) [, dia, mes, ano, hora, minuto] = m;
  else return null;
  const [a, me, d, h, mi, s] = [ano, mes, dia, hora || 0, minuto || 0, seg || 0].map(Number);
  const data = new Date(Date.UTC(a, me - 1, d, h, mi, s));
  if (data.getUTCFullYear() !== a || data.getUTCMonth() !== me - 1 || data.getUTCDate() !== d || h > 23 || mi > 59 || s > 59) return null;
  let segundos = Math.floor(data.getTime() / 1000);
  if (fuso && fuso !== "Z") {
    const limpo = fuso.replace(":", ""), desloc = (Number(limpo.slice(1, 3)) * 60 + Number(limpo.slice(3, 5))) * 60;
    segundos -= limpo[0] === "+" ? desloc : -desloc;
  }
  return segundos;
}

export const iso = (segundos) => new Date(segundos * 1000).toISOString().slice(0, 19);

export function maturidade(post, agora) {
  const quando = epoch(post.data);
  if (quando == null) return "sem_data";
  return agora - quando >= HORAS_MADURO * 3600 ? "maduro" : "imaturo";
}

export const confianca = (nMaduros) => (nMaduros < MIN_POSTS_PERFIL ? "baixa" : "ok");

// Legenda é dado de terceiros: uma linha, sem caracteres de controle, no máximo 200 caracteres.
export const limparLegenda = (texto) => Array.from((texto ?? "").toString().replace(/[\x00-\x1f\x7f]/g, " ").split(/\s+/).filter(Boolean).join(" ")).slice(0, MAX_LEGENDA).join("").trim();

const REGRAS = [
  ["numero", /\d/],
  ["polemica", /\b(mito|mitos|verdade|ninguem|erro|erros|nunca|pare de|segredo|chocante|polemic\w*|cuidado|enganad\w*|mentira|proibido)\b/],
  ["promessa", /\b(como|aprenda|aprender|passo a passo|guia|descubra|dicas?|truque|metodo)\b/],
  ["historia", /\b(quando eu|eu (fui|era|tinha|perdi|comecei|descobri|fiz|vivi|ganhei)|minha historia|um dia|certa vez)\b/],
  ["urgencia", /\b(hoje|agora|ultimas? (vagas|horas|dias|chances?)|so ate|ate (amanha|domingo|sexta)|acaba|corra|urgente|ultimo dia)\b/],
];
const CTA = /\b(comente|comenta|comentem|comentar|deixe? (aqui |nos )?(nos )?comentarios|digite|escreva (a palavra|aqui|nos comentarios)|me manda|manda (a palavra|aqui)|palavra[- ]chave)\b/;

export const primeiraFrase = (legenda) => String(legenda ?? "").trim().split(/(?<=[.!?])\s+|\n+/).find((p) => p.trim()) ?? "";

export function classificarGancho(legenda) {
  const frase = primeiraFrase(legenda);
  if (frase.includes("?")) return "pergunta";
  const baixo = fold(frase);
  return REGRAS.find(([, regra]) => regra.test(baixo))?.[0] ?? "indefinido";
}

export const temCtaComentario = (legenda) => CTA.test(fold(legenda ?? ""));

// ── identidade do post e normalização (importação) ───────────────────────
export function normalizarFormato(valor) {
  const t = fold(valor ?? "").trim();
  if (/reel|video|clip/.test(t)) return "reels";
  if (/carrossel|carousel|sidecar|album/.test(t)) return "carrossel";
  if (/imagem|image|foto|photo|^post$/.test(t)) return "imagem";
  return t.replace(/[^a-z0-9 ]/g, "").slice(0, 20).trim() || "outro";
}

export function normalizarPerfil(valor) {
  let t = String(valor ?? "").trim().toLowerCase().replace(/^https?:\/\/(www\.)?instagram\.com\//, "").split("/")[0].split("?")[0];
  t = t.replace(/^@+/, "").replace(/[^a-z0-9._]/g, "");
  return t ? "@" + t.slice(0, 30) : "";
}

export function limparLink(valor) {
  const t = String(valor ?? "").trim().split("?")[0].split("#")[0].replace(/\/+$/, "");
  return /^http/i.test(t) ? t.slice(0, 200) : "";
}

export function chavePost(post) {
  const link = post.link || "";
  const achado = /\/(?:p|reel|reels|tv)\/([A-Za-z0-9_-]+)/.exec(link);
  if (achado) return "ig:" + achado[1];
  if (link) return link.toLowerCase();
  return `${post.perfil}|${post.data}|${fold(post.legenda ?? "").slice(0, 40)}`;
}

// Texto para o casador de intenções (sem IA). É o espelho de jarvis/local/nlp.py (PC): mesmas palavras vazias, mesmos sinônimos, mesma
// tokenização, mesma distância de edição e mesmos trigramas; o teste de paridade confere. A única diferença: o radical. O PC usa o
// snowballstemmer (Python); aqui, um radical simples próprio (tira plural, sufixo comum e vogal final), porque o app não tem biblioteca.
import { fold } from "./util.js";

// "nao" e "como" ficam de fora de propósito: carregam sentido ("não ouço", "como instalar").
export const PALAVRAS_VAZIAS = new Set(`a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela para pra pro com sem sobre ao aos
e ou que se meu minha meus minhas seu sua teu tua me te lhe mim ti eu tu ele ela ja so ate la ai aqui isso isto esse essa
este esta esses essas aquele aquela mais muito muita bem tambem entao pois mas quando qual quais foi ser sao era tem ter tenho
pode posso poderia quero queria gostaria preciso gosto vou vai estou esta estao estar favor pfv pf
ei ok oi ola hey tipo assim coisa`.split(/\s+/));

// Variações comuns de fala e escrita levadas a uma palavra só (antes do radical).
export const SINONIMOS = {
  telefone: "celular", smartphone: "celular", aparelho: "celular", cel: "celular", mobile: "celular", fone: "celular",
  ipad: "celular", iphone: "iphone", ios: "iphone", apple: "iphone", safari: "iphone", droid: "android",
  javis: "jarvis", jarvs: "jarvis", jarves: "jarvis", jarbis: "jarvis", jarvi: "jarvis", garvis: "jarvis", jarvez: "jarvis",
  senha: "chave", token: "chave", api: "chave",
  microfone: "escuta", mic: "escuta", ouvir: "escuta", ouvindo: "escuta", ouve: "escuta", ouco: "escuta", escutar: "escuta", escutando: "escuta", escuta: "escuta",
  falar: "voz", fala: "voz", falando: "voz", som: "voz", audio: "voz",
  backup: "copia", seguranca: "copia", exportar: "copia", salvar: "copia",
  importar: "restaurar", recuperar: "restaurar", migrar: "levar", transferir: "levar", passar: "levar", trocar: "levar",
  remover: "desinstalar", excluir: "desinstalar", baixar: "instalar", colocar: "instalar", botar: "instalar",
  versao: "atualizar", update: "atualizar", novidade: "atualizar", atualizacao: "atualizar",
  cor: "tema", cores: "tema", visual: "tema", aparencia: "tema", escuro: "tema", claro: "tema",
  janelas: "caixas", janela: "caixas", paineis: "caixas", painel: "caixas", cartoes: "caixas",
  calendario: "agenda", compromissos: "agenda", gmail: "email", emails: "email", mail: "email", outlook: "email",
  travando: "travar", trava: "travar", travou: "travar", lenta: "lento", lerda: "lento", demora: "lento", demorando: "lento",
  bug: "erro", problema: "erro", falha: "erro", falhou: "erro", quebrou: "erro", defeito: "erro",
  limite: "cota", gasto: "cota", gastei: "cota", noticia: "noticias", manchetes: "noticias", ia: "ia", inteligencia: "ia",
};

const SUFIXOS = ["amentos", "imentos", "amento", "imento", "adores", "adoras", "mente", "acoes", "icoes", "ucoes", "acao", "icao", "ucao", "idade", "ando", "endo", "indo",
  "ados", "adas", "idos", "idas", "ado", "ada", "ido", "ida", "ou", "am", "ar", "er", "ir", "ia"];

export const normalizar = (texto) => fold(texto).replace(/(?<=[a-z])-(?=[a-z])/g, "").replace(/[^a-z0-9]+/g, " ").trim();
export const palavras = (texto) => normalizar(texto).split(" ").filter(Boolean);

// Radical simples: tira plural, sufixo comum e vogal final. O mesmo cálculo vale para a frase e para os exemplos, então só precisa ser consistente.
const guarda = new Map();
export function radical(p) {
  const nova = SINONIMOS[p] || p;
  if (guarda.has(nova)) return guarda.get(nova);
  let r = nova;
  if (r.length > 4 && /[rzl]es$/.test(r)) r = r.slice(0, -2);
  else if (r.length > 3 && r.endsWith("s") && !r.endsWith("ss")) r = r.slice(0, -1);
  for (const s of SUFIXOS) if (r.length - s.length >= 3 && r.endsWith(s)) { r = r.slice(0, -s.length); break; }
  if (r.length > 4 && /[aeo]$/.test(r)) r = r.slice(0, -1);
  if (guarda.size > 8192) guarda.clear();
  guarda.set(nova, r);
  return r;
}

// Distância de Damerau-Levenshtein (troca de letras vizinhas conta 1: "celualr" ~ "celular"). Acima de 3 de diferença de tamanho, 99.
export function distancia(a, b) {
  if (Math.abs(a.length - b.length) > 3) return 99;
  let anterior2 = null, anterior = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const atual = [i];
    for (let j = 1; j <= b.length; j++) {
      let v = Math.min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      if (anterior2 && i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) v = Math.min(v, anterior2[j - 2] + 1);
      atual.push(v);
    }
    anterior2 = anterior; anterior = atual;
  }
  return anterior[b.length];
}

// Troca uma palavra desconhecida pela mais próxima do vocabulário (1 erro até 6 letras, 2 acima). Curtas ficam como estão.
// Extras do celular (o PC não tem): o "h" mudo que o ditado come ("oras" ~ "hora") e palavras de 3 letras com 1 erro e a mesma inicial ("dta" ~ "data").
export function corrigir(palavra, vocabulario) {
  if (vocabulario.has(palavra) || /^\d+$/.test(palavra)) return palavra;
  if (palavra.length < 3 || PALAVRAS_VAZIAS.has(palavra)) return palavra;  // palavra vazia nunca vira outra coisa ("que" não é "quem")
  const limite = palavra.length <= 6 ? 1 : 2;
  let melhor = palavra, melhorD = limite + 1;
  for (const c of vocabulario) {
    if (c === "h" + palavra) { if (melhorD > 1 || c < melhor) { melhor = c; melhorD = 1; } continue; }
    if (palavra.length < 4 && (c[0] !== palavra[0] || c.length !== 4)) continue;
    if (Math.abs(c.length - palavra.length) > limite || (c[0] !== palavra[0] && limite === 1 && palavra.length <= 4)) continue;
    const d = distancia(palavra, c);
    if (d < melhorD || (d === melhorD && d <= limite && c < melhor)) { melhor = c; melhorD = d; }
  }
  return melhorD <= limite ? melhor : palavra;
}

// Radicais úteis do texto (sem palavras vazias), com erros de digitação corrigidos pelo vocabulário conhecido.
export function termos(texto, vocabulario = null) {
  const saida = [];
  for (let p of palavras(texto)) {
    if (vocabulario?.size) p = corrigir(p, vocabulario);
    if (!PALAVRAS_VAZIAS.has(p)) saida.push(radical(p));
  }
  return saida;
}

export function trigramas(texto) {
  const base = ` ${palavras(texto).join(" ")} `, conjunto = new Set();
  for (let i = 0; i + 3 <= base.length; i++) conjunto.add(base.slice(i, i + 3));
  return conjunto;
}

export function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let comum = 0;
  for (const x of a) if (b.has(x)) comum++;
  return comum / (a.size + b.size - comum);
}

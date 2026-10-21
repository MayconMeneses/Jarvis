// Restauração segura da cópia de segurança: o arquivo é DADO de terceiros (pode ter sido adulterado).
// Só voltam as notas bem formadas e as configurações da LISTA BRANCA abaixo, cada uma com tipo e tamanho conferidos.
// Nunca voltam: autonomo:* (liga o modo autônomo), segredo:*/pc:* (chaves e token do PC, nem entram na cópia), caches, batimentos de agentes
// e "cerebro" (religar sozinho baixaria um modelo). O que for recusado é contado e informado ao usuário.
export const MAX_ARQUIVO = 30_000_000;   // caracteres do arquivo inteiro
export const MAX_NOTAS = 10000;
const MAX_REF = 120, MAX_CORPO = 20000;

const simples = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const texto = (max, minimo = 0) => (v) => typeof v === "string" && v.length >= minimo && v.length <= max;
const token = (max) => (v) => typeof v === "string" && v.length > 0 && v.length <= max && /^[\w:.-]+$/.test(v);
const opcao = (...itens) => (v) => itens.includes(v);
const booleano = (v) => typeof v === "boolean";
const tamanhoJson = (v) => { try { return JSON.stringify(v)?.length ?? 0; } catch { return Infinity; } };
const limitado = (max) => (v) => tamanhoJson(v) <= max && !JSON.stringify(v).includes('"__proto__"');

const mensagemOk = (m) => simples(m) && (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content.length <= 4000;
const avaliacaoOk = (a) => simples(a) && typeof a.quando === "string" && a.quando.length <= 40 && typeof a.modelo === "string" && a.modelo.length <= 120
  && Number.isFinite(a.nota) && Number.isFinite(a.acertos) && Number.isFinite(a.total) && simples(a.detalhes || {}) && limitado(5000)(a.detalhes || {});
const postsOk = (r) => simples(r) && Number.isFinite(r.id) && typeof r.criada === "string" && r.criada.length <= 40 && simples(r.posts) && Object.values(r.posts).every(simples);
const instagramOk = (v) => simples(v) && limitado(1_500_000)(v) && (v.analise === undefined || simples(v.analise)) && (v.seguidores === undefined || simples(v.seguidores))
  && (v.lembrete === undefined || booleano(v.lembrete)) && (v.rodadas === undefined || (Array.isArray(v.rodadas) && v.rodadas.length <= 12 && v.rodadas.every(postsOk)));
const usoMesOk = (v) => simples(v) && limitado(200_000)(v);

// Chave exata ou prefixo+padrão => validador do valor. Valor nulo/undefined nunca é gravado.
const EXATAS = {
  nome: texto(60, 1), cidade: texto(80, 1), tema: token(30), orbe_modo: opcao("auto", "completo", "suave", "desligado"),
  falar: booleano, nuvem_ordem: opcao("aparelho", "nuvem"),
  voz_foco_auto: booleano, voz_escuta_conversa: booleano, voz_navegador_voz: texto(200),  // voz_provedor (Gemini) fica de fora de propósito: o aviso de privacidade é por aparelho
  conversa: (v) => Array.isArray(v) && v.length <= 200 && v.every(mensagemOk), avaliacoes: (v) => Array.isArray(v) && v.length <= 30 && v.every(avaliacaoOk),
  instagram: instagramOk, "oficina:projetos": (v) => Array.isArray(v) && v.length <= 200 && v.every((p) => typeof p === "string" && p.length > 0 && p.length <= 60),
  "uso:config": (v) => simples(v) && limitado(20_000)(v),
};
const PADROES = [[/^uso:\d{4}-\d{2}$/, usoMesOk], [/^aviso:[\w:-]{1,60}$/, booleano]];

export function validadorMeta(chave) {
  if (typeof chave !== "string" || chave.length > 80) return null;
  if (Object.hasOwn(EXATAS, chave)) return EXATAS[chave];
  return PADROES.find(([re]) => re.test(chave))?.[1] || null;
}

export function notaLimpa(n) {
  if (!simples(n) || typeof n.ref !== "string" || typeof n.corpo !== "string") return null;
  const ref = n.ref.trim().replace(/\s+/g, " ").slice(0, MAX_REF);
  if (!ref) return null;
  const data = (v) => (typeof v === "string" && v.length <= 40 && !Number.isNaN(Date.parse(v)) ? v : new Date(0).toISOString());
  const atualizada = data(n.atualizada);
  return { ref, titulo: typeof n.titulo === "string" && n.titulo ? n.titulo.slice(0, 200) : ref.split("/").pop(), tipo: typeof n.tipo === "string" ? n.tipo.slice(0, 30) : "nota",
    corpo: n.corpo.slice(0, MAX_CORPO), criada: typeof n.criada === "string" && !Number.isNaN(Date.parse(n.criada)) ? n.criada : atualizada, atualizada };
}

// Lê o JSON, separa o que vale do que não vale. Devolve { notas: [...limpas], meta: {chave: valor}, ignoradas: { notas, meta: [chaves] } }.
export function lerCopia(conteudo) {
  if (typeof conteudo !== "string" || conteudo.length > MAX_ARQUIVO) throw new Error("arquivo de cópia grande demais ou inválido");
  let dados;
  try { dados = JSON.parse(conteudo); } catch { throw new Error("arquivo de cópia inválido"); }
  if (!simples(dados) || dados.formato !== "jarvis-movel-1" || !Array.isArray(dados.notas)) throw new Error("arquivo de cópia inválido");
  const notas = [], resultado = { notas, meta: {}, ignoradas: { notas: 0, meta: [] } };
  for (const n of dados.notas.slice(0, MAX_NOTAS)) { const limpa = notaLimpa(n); if (limpa) notas.push(limpa); else resultado.ignoradas.notas++; }
  resultado.ignoradas.notas += Math.max(0, dados.notas.length - MAX_NOTAS);
  const meta = simples(dados.meta) ? dados.meta : {};
  for (const [chave, valor] of Object.entries(meta)) {
    const valida = validadorMeta(chave);
    if (valida && valor !== null && valor !== undefined && valida(valor)) resultado.meta[chave] = valor; else resultado.ignoradas.meta.push(chave.slice(0, 40));
  }
  return resultado;
}

export function resumoRestauracao({ notas, meta, ignoradas }) {
  const ig = ignoradas.notas + ignoradas.meta.length;
  return `Restaurei ${notas.length} notas e ${Object.keys(meta).length} configurações.` + (ig ? ` Ignorei ${ig} item(ns) inválido(s) ou não permitido(s) no arquivo${ignoradas.meta.length ? " (configurações: " + ignoradas.meta.slice(0, 5).join(", ") + ")" : ""}.` : "");
}

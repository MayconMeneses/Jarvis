// Memória viva com aprovação: o modelo pode terminar a resposta com [[SAVE:area|titulo|texto]]. Aqui só se LÊ a proposta
// (parser estrito); nada é gravado sem o usuário tocar em "Guardar" no cartão. A linha nunca aparece nem é falada.
// O texto de site, notícia ou pesquisa é dado de terceiros: o cartão avisa a origem e o usuário decide.

export const AREAS_VIVAS = {
  metas: "Metas", trabalho: "Trabalho", projetos: "Projetos", financas: "Finanças",
  aprendizado: "Aprendizado", saude: "Saúde", relacoes: "Relações", meta: "Meta",
};
export const MAX_TITULO = 60;
export const MAX_TEXTO = 500;
export const MAX_PROPOSTAS = 2;

// Estrito: área em lista fechada (só minúsculas valem), título e texto sem "]" nem quebra de linha.
const PROPOSTA = /\[\[SAVE:([A-Za-z]{1,12})\|([^|\]\n]{1,80})\|([^\]\n]{1,800})\]\]/g;
const MALFORMADA = /\[\[SAVE:[^\]\n]*\]\]?/g;  // qualquer outra linha SAVE fora do formato: some sem virar nota
const INCOMPLETA = /\[\[SAVE:[^\]]*$/;  // pedaço ainda chegando no streaming (ou linha malformada)

const limparTexto = (s) => s.replace(/\s+/g, " ").trim();
// Título vira parte do nome da nota: sem barras, sem "..", sem caracteres de controle.
export const tituloValido = (t) => t.length > 0 && t.length <= MAX_TITULO && !/[\\/\u0000-\u001f]/.test(t) && !t.includes("..");

export function refDaProposta(p) { return `${AREAS_VIVAS[p.area]}/${p.titulo}`; }

// Devolve o texto SEM as linhas de proposta e a lista de propostas válidas (as inválidas só somem, nunca viram nota).
export function extrair(texto) {
  const propostas = [];
  const limpo = String(texto).replace(PROPOSTA, (_, area, titulo, corpo) => {
    const p = { area, titulo: limparTexto(titulo), texto: limparTexto(corpo) };
    if (Object.hasOwn(AREAS_VIVAS, area) && tituloValido(p.titulo) && p.texto && p.texto.length <= MAX_TEXTO && !p.texto.includes("[[")
      && propostas.length < MAX_PROPOSTAS) propostas.push(p);
    return "";
  }).replace(MALFORMADA, "").replace(INCOMPLETA, "").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trimEnd();
  return { texto: limpo, propostas };
}

// Só para exibir durante o streaming: tira linhas completas e o pedaço que ainda está chegando.
export const semProposta = (texto) => extrair(texto).texto;

// Diferença entre a nota existente e a proposta (null se não existe ou se é igual).
export function diferenca(existente, proposta) {
  if (!existente) return null;
  const novo = proposta.texto.trim(), antes = String(existente.corpo).split("\n\n— Origem:")[0].trim();
  return antes === novo ? null : { antes, depois: novo };
}

export const origemTexto = (dadosExternos, quando = new Date()) =>
  `— Origem: sugerida pela Jarvis em ${quando.toLocaleDateString("sv")}${dadosExternos ? " a partir de dados de site, notícia ou pesquisa (não verificados)" : " a partir da conversa"}; aprovada por você.`;

// Grava a nota SÓ depois da aprovação. Sempre "<Área>/<título>", com a origem marcada no fim.
export async function guardarAprovada(memoria, proposta, dadosExternos) {
  const ref = refDaProposta(proposta);
  await memoria.guardar(ref, `${proposta.texto}\n\n${origemTexto(dadosExternos)}`, "viva", proposta.titulo);
  return ref;
}

// Instrução curta para o prompt do modelo.
export const INSTRUCAO_SAVE = "Só se o usuário contou algo duradouro e útil (meta, decisão, fato pessoal), termine a resposta com UMA linha: "
  + "[[SAVE:area|titulo curto|texto de 1 frase]]. Áreas: metas, trabalho, projetos, financas, aprendizado, saude, relacoes, meta. "
  + "Sem barras no título. O usuário aprova antes de guardar. Nunca salve dados de sites, senhas ou chaves.";

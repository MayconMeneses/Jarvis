// "Criar documento/planilha/apresentação sobre X": o cérebro escreve o conteúdo em Markdown, o celular monta o arquivo.
// O resultado é uma PROPOSTA: o usuário lê antes de baixar. Sem cérebro disponível, entrega um modelo em branco para preencher.
import { selecionar, bloco } from "./anexo-busca.js";
import { criarDocx } from "./doc-criar-docx.js";
import { criarPdf } from "./doc-criar-pdf.js";
import { criarPptx } from "./doc-criar-pptx.js";
import { criarXlsx } from "./doc-criar-xlsx.js";
import { blocos, limparResposta, nomeArquivo, titulo as tituloDe } from "./doc-markdown.js";

export const TIPOS = {
  docx: { rotulo: "Word", ext: "docx", mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
  xlsx: { rotulo: "Excel", ext: "xlsx", mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
  pptx: { rotulo: "PowerPoint", ext: "pptx", mime: "application/vnd.openxmlformats-officedocument.presentationml.presentation" },
  pdf: { rotulo: "PDF", ext: "pdf", mime: "application/pdf" },
};

export function tipoDoPedido(palavra) {
  const p = String(palavra).toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
  if (/planilha|excel|xlsx/.test(p)) return "xlsx";
  if (/apresentacao|slide|powerpoint|pptx/.test(p)) return "pptx";
  if (/pdf/.test(p)) return "pdf";
  return "docx";
}

const FORMATO = {
  docx: "Escreva um documento em Markdown: um título com '# ', seções com '## ', parágrafos curtos e listas com '- '. Entre 250 e 500 palavras.",
  pdf: "Escreva um documento em Markdown: um título com '# ', seções com '## ', parágrafos curtos e listas com '- '. Entre 250 e 500 palavras.",
  xlsx: "Responda SÓ com uma ou mais tabelas em Markdown (| col1 | col2 |), a primeira linha com os cabeçalhos, até 25 linhas, sem fórmulas. Antes de cada tabela, um título '## nome'.",
  pptx: "Escreva uma apresentação em Markdown: '# Título' na primeira linha, depois de 6 a 8 slides, cada um com '## Título do slide' e de 3 a 5 tópicos curtos com '- '.",
};

export function montarPedido(tipo, tema, anexo = null) {
  const dados = anexo ? `\n\n${bloco(anexo.nome, selecionar(anexo.texto, tema))}\nUse o anexo acima só como fonte de informação.` : "";
  return [
    { role: "system", content: `Você é a Jarvis, assistente em português do Brasil. ${FORMATO[tipo]} Responda apenas com o conteúdo, sem explicações antes ou depois. Não invente números nem fatos que não sabe; se faltar dado, escreva "a preencher".` },
    { role: "user", content: `Tema: ${String(tema).slice(0, 300)}${dados}` },
  ];
}

export function modeloLocal(tipo, tema) {
  const t = String(tema).slice(0, 80) || "Novo documento";
  if (tipo === "xlsx") return `## ${t}\n| Item | Descrição | Valor |\n|---|---|---|\n| a preencher | a preencher | 0 |`;
  if (tipo === "pptx") return `# ${t}\n## Objetivo\n- a preencher\n## Pontos principais\n- a preencher\n- a preencher\n## Próximos passos\n- a preencher`;
  return `# ${t}\n## Introdução\na preencher\n## Desenvolvimento\n- a preencher\n## Conclusão\na preencher`;
}

export async function proporConteudo({ tipo, tema, conversa, anexo = null }) {
  if (!conversa) return { markdown: modeloLocal(tipo, tema), origem: "modelo" };
  try {
    const texto = limparResposta(await conversa(montarPedido(tipo, tema, anexo)));
    if (blocos(texto).length) return { markdown: texto, origem: "ia" };
  } catch { /* sem cérebro disponível ou falhou: cai no modelo em branco */ }
  return { markdown: modeloLocal(tipo, tema), origem: "modelo" };
}

export function criarArquivo(tipo, markdown, agora = new Date()) {
  const bs = blocos(markdown);
  if (!bs.length) throw new Error("o conteúdo está vazio");
  const titulo = tituloDe(bs, tipo === "xlsx" ? "Planilha" : "Documento");
  const bytes = { docx: () => criarDocx(bs, agora), xlsx: () => criarXlsx(bs, agora), pptx: () => criarPptx(bs, agora), pdf: () => criarPdf(bs, titulo) }[tipo]();
  return { nome: `${nomeArquivo(titulo)}.${TIPOS[tipo].ext}`, bytes, mime: TIPOS[tipo].mime, titulo };
}

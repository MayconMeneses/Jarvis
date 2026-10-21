// Aba "Documentos": anexar e consultar um arquivo, criar Word/Excel/PowerPoint/PDF (proposta antes de baixar) e pesquisar em níveis.
// Contrato com a casca: montarDocumentos(container, { documentos, avisar }). Tudo é montado com textContent (nada de innerHTML).
import { entregar } from "./doc-baixar.js";
import { TIPOS } from "./doc-proposta.js";
import { NIVEIS } from "./pesquisa-niveis.js";

const ACEITA = ".txt,.md,.csv,.json,.pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.heic,text/*,image/*";

function el(doc, tag, props = {}, ...filhos) {
  const e = Object.assign(doc.createElement(tag), props);
  e.append(...filhos);
  return e;
}
const botao = (doc, texto, aoTocar) => { const b = el(doc, "button", { type: "button", textContent: texto }); b.addEventListener("click", aoTocar); return b; };
const campo = (doc, id, rotulo, controle) => { controle.id = id; return [el(doc, "label", { htmlFor: id, textContent: rotulo }), controle]; };

export function montarDocumentos(container, { documentos, avisar = () => {}, doc = container.ownerDocument } = {}) {
  const saida = (id) => el(doc, "pre", { id, hidden: true });
  const mostrar = (pre, texto) => { pre.textContent = texto; pre.hidden = !texto; };

  // 1. Anexo
  const arquivo = el(doc, "input", { type: "file", accept: ACEITA });
  const estadoAnexo = el(doc, "p", { className: "nota", id: "doc-anexo-estado", textContent: "Nenhum arquivo escolhido." });
  const resposta = saida("doc-resposta");
  const pergunta = el(doc, "input", { autocomplete: "off", enterkeyhint: "send", placeholder: "Pergunte algo sobre o arquivo" });
  const rodar = async (fn) => { try { mostrar(resposta, "Pensando…"); mostrar(resposta, await fn()); } catch (e) { mostrar(resposta, ""); avisar(e.message); } };
  arquivo.addEventListener("change", async () => {
    const f = arquivo.files?.[0];
    if (!f) return;
    estadoAnexo.textContent = `Lendo "${f.name}"…`;
    try { await documentos.anexar(f); } catch (e) { estadoAnexo.textContent = "Não consegui ler o arquivo."; avisar(e.message); }
    arquivo.value = "";
  });
  const secaoAnexo = el(doc, "section", { className: "documentos-anexo" },
    el(doc, "h3", { textContent: "Anexo" }), arquivo, estadoAnexo,
    el(doc, "div", { className: "linha" }, botao(doc, "Resumir", () => rodar(() => documentos.resumir())), botao(doc, "Limpar anexo", () => { documentos.limparAnexo(); mostrar(resposta, ""); })),
    ...campo(doc, "doc-pergunta", "Pergunta sobre o anexo", pergunta),
    botao(doc, "Perguntar", () => pergunta.value.trim() && rodar(() => documentos.perguntar(pergunta.value))), resposta,
    el(doc, "p", { className: "nota", textContent: "O conteúdo do arquivo é tratado como dado, nunca como ordem. Imagens precisam da chave Gemini (aba Cérebro)." }));

  // 2. Criar documento
  const tipo = el(doc, "select");
  for (const [id, t] of Object.entries(TIPOS)) tipo.append(el(doc, "option", { value: id, textContent: t.rotulo }));
  const tema = el(doc, "input", { autocomplete: "off", maxLength: 300, placeholder: "Sobre o quê?" });
  const usarAnexo = el(doc, "input", { type: "checkbox" });
  const editor = el(doc, "textarea", { rows: 12, hidden: true, spellcheck: false });
  const estadoProposta = el(doc, "p", { className: "nota", hidden: true });
  const entregarBtn = botao(doc, "Baixar / compartilhar", async () => {
    try {
      documentos.editarProposta(editor.value);
      const r = await entregar(documentos.arquivoDaProposta(), { doc });
      if (r !== "cancelado") avisar(r === "baixado" ? "Arquivo baixado (veja em Arquivos > Downloads)." : "Compartilhado.");
    } catch (e) { avisar("Não consegui criar o arquivo: " + e.message); }
  });
  const descartarBtn = botao(doc, "Descartar", () => documentos.descartarProposta());
  const acoes = el(doc, "div", { className: "linha", hidden: true }, entregarBtn, descartarBtn);
  const preparar = botao(doc, "Preparar proposta", async () => {
    if (tema.value.trim().length < 3) return avisar("Diga o tema do documento.");
    preparar.disabled = true;
    estadoProposta.hidden = false; estadoProposta.textContent = "Escrevendo a proposta…";
    try { await documentos.propor(tipo.value, tema.value.trim(), { usarAnexo: usarAnexo.checked }); } catch (e) { estadoProposta.hidden = true; avisar(e.message); } finally { preparar.disabled = false; }
  });
  const secaoCriar = el(doc, "section", { className: "documentos-criar" }, el(doc, "h3", { textContent: "Criar documento" }),
    ...campo(doc, "doc-tipo", "Tipo", tipo), ...campo(doc, "doc-tema", "Tema", tema),
    el(doc, "label", { className: "voz" }, usarAnexo, " Usar o anexo como fonte"), preparar, estadoProposta, editor, acoes,
    el(doc, "p", { className: "nota", textContent: "A IA escreve uma proposta; você lê e edita aqui antes de baixar. Nada é baixado sozinho." }));

  // 3. Pesquisa em níveis
  const assunto = el(doc, "input", { autocomplete: "off", maxLength: 120, placeholder: "O que pesquisar?" });
  const nivel = el(doc, "select");
  for (const [id, n] of Object.entries(NIVEIS)) nivel.append(el(doc, "option", { value: id, textContent: `${n.nome[0].toUpperCase()}${n.nome.slice(1)} (até ${n.maxChamadas} buscas)`, selected: id === "medio" }));
  const estadoPesquisa = el(doc, "p", { className: "nota", id: "doc-pesquisa-estado", hidden: true });
  const resultado = saida("doc-pesquisa-resultado");
  const cancelar = botao(doc, "Cancelar", () => documentos.cancelarPesquisa());
  cancelar.hidden = true;
  const pesquisar = botao(doc, "Pesquisar", async () => {
    if (assunto.value.trim().length < 3) return avisar("Diga o que pesquisar.");
    pesquisar.disabled = true; cancelar.hidden = false; mostrar(resultado, "");
    const frase = { buscando: (e) => `Buscando ${e.passo} de ${e.de}: ${e.consulta} (${e.fontes} fontes)`, resumindo: (e) => `Resumindo ${e.fontes} fontes…`, cancelada: () => "Cancelada.", pronta: () => "Pronta.", erro: (e) => "Erro: " + e.erro };
    try {
      const r = await documentos.pesquisar(assunto.value, nivel.value, (e) => { estadoPesquisa.hidden = false; estadoPesquisa.textContent = frase[e.fase]?.(e) || ""; });
      mostrar(resultado, r.texto);
    } catch (e) { avisar("A pesquisa falhou: " + e.message); } finally { pesquisar.disabled = false; cancelar.hidden = true; }
  });
  const secaoPesquisa = el(doc, "section", { className: "documentos-pesquisa" }, el(doc, "h3", { textContent: "Pesquisa em níveis" }),
    ...campo(doc, "doc-assunto", "Assunto", assunto), ...campo(doc, "doc-nivel", "Nível", nivel),
    el(doc, "div", { className: "linha" }, pesquisar, cancelar), estadoPesquisa, resultado,
    el(doc, "p", { className: "nota", textContent: "Usa o Brave (se você cadastrou o proxy) ou a Wikipédia. Mostra as fontes, guarda o resultado na Memória e não é verificado." }));

  container.replaceChildren(secaoAnexo, secaoCriar, secaoPesquisa);

  let vista = null;
  const atualizar = () => {
    const a = documentos.anexo;
    estadoAnexo.textContent = a ? `${a.nome} (${a.tipo}, ${a.texto.length} caracteres)${a.avisos.length ? ". Aviso: " + a.avisos.join("; ") : ""}` : "Nenhum arquivo escolhido.";
    const p = documentos.proposta;
    editor.hidden = acoes.hidden = estadoProposta.hidden = !p;
    if (p) {
      if (p !== vista) editor.value = p.markdown;
      vista = p;
      estadoProposta.textContent = p.origem === "modelo" ? "Modelo em branco (sem cérebro disponível). Edite e baixe." : p.origem === "ia" ? "Proposta escrita pela IA: confira e edite antes de baixar." : "Editada por você.";
    }
  };
  documentos.aoMudar(atualizar);
  atualizar();
  return { atualizar };
}

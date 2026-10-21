// Comandos de chat para anexos, documentos e pesquisa em níveis. Entram na frente da lista de padrões do motor (frases bem específicas).
import { TIPOS, tipoDoPedido } from "./doc-proposta.js";
import { nivelDe, semSaudacao, temaDePesquisa } from "./pesquisa-niveis.js";

const TIPO_RE = "documento|doc|word|relatorio|planilha|excel|apresentacao|slides?|powerpoint|pdf";
const TIPO_ACENTO = "documento|doc|word|relat[óo]rio|planilha|excel|apresenta[çc][ãa]o|slides?|powerpoint|pdf";
const DOCUMENTOS = [
  ["criar_documento", new RegExp(`^(cri[ae]\\w*|ger[ae]\\w*|faca|fazer|mont[ae]\\w*|prepar\\w+|escrev\\w+)\\s+(um|uma|o|a)?\\s*(${TIPO_RE})\\b.*$`)],
  ["resumir_anexo", /^(resum\w+|leia|ler|analis\w+)\s+(o\s+)?(anexo|arquivo anexad\w+)\b.*$|^o que (diz|tem|fala)\s+(o|no)\s+anexo\b.*$/],
  ["perguntar_anexo", /\b(no|do|desse|deste|neste|nesse|sobre o)\s+(anexo|arquivo anexado)\b/],
  ["cancelar_pesquisa", /^(cancel\w+|par[ae]\w*)\s+(a\s+)?pesquisa$/],
  ["pesquisa_niveis", /^pesquis\w*\s+(a fundo|profundamente|rapid\w*|medi[ao]|profund\w*|em niveis)\b.*$|^pesquis\w*\s+.+\s+nivel\s+(rapido|medio|profundo)$/],
];

const SEM = "A parte de documentos ainda não está pronta neste aparelho.";

const HANDLERS = {
  async _criar_documento(texto, limpo) {
    if (!this.documentos) return SEM;
    const tipo = tipoDoPedido(new RegExp(`(${TIPO_RE})`).exec(limpo)[1]);
    const tema = semSaudacao(texto).replace(new RegExp(`^\\s*\\S+\\s+(?:um|uma|o|a)?\\s*(?:${TIPO_ACENTO})\\s*(?:de|do|da|sobre|com|para|a respeito de)?\\s*`, "i"), "").replace(/[?!. ]+$/, "").trim();
    if (tema.length < 3) return `Sobre o quê? Exemplo: "crie uma apresentação sobre ${tipo === "xlsx" ? "controle de gastos" : "segurança no celular"}".`;
    const usarAnexo = /\b(anexo|arquivo anexado)\b/.test(limpo) && Boolean(this.documentos.anexo);
    const p = await this.documentos.propor(tipo, tema, { usarAnexo });
    const aviso = p.origem === "modelo" ? "Sem cérebro disponível, montei um MODELO em branco para você preencher." : "Conteúdo escrito pela IA: confira antes de usar.";
    return `Preparei uma **proposta de ${TIPOS[tipo].rotulo}** sobre "${tema}". ${aviso}\nAbra a aba **Documentos** (em Mais) para ler, editar e baixar ou compartilhar. Nada foi baixado ainda.\n\n${p.markdown.slice(0, 700)}${p.markdown.length > 700 ? "\n…" : ""}`;
  },

  async _resumir_anexo() { return this.documentos ? this.documentos.resumir() : SEM; },
  async _perguntar_anexo(texto) { return this.documentos ? this.documentos.perguntar(texto) : SEM; },

  _cancelar_pesquisa() { return this.documentos?.cancelarPesquisa() ? "Cancelando a pesquisa…" : "Não há pesquisa em andamento."; },

  async _pesquisa_niveis(texto) {
    if (!this.documentos) return SEM;
    const nivel = nivelDe(texto) || "medio";
    const tema = temaDePesquisa(texto);
    if (tema.length < 3) return 'Sobre o quê? Exemplo: "pesquisar a fundo energia solar".';
    const r = await this.documentos.pesquisar(tema, nivel);
    return r.texto;
  },
};

export function instalarDocumentos(Motor, padroes) {
  padroes.unshift(...DOCUMENTOS);
  Object.assign(Motor.prototype, HANDLERS);
}

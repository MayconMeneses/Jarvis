// Mais pedidos do motor, os mesmos do PC: clima, notícias, vagas, perfil, projetos, habilidades, stack e revisão de código.
// Entram na frente da lista de padrões (são frases bem específicas); os handlers viram métodos do Motor.
import { atualizarPerfil, clima, noticias, vagas } from "./info.js";
import { relatorio as relatorioRevisao } from "./revisao.js";
import { fold } from "./util.js";

const EXTRAS = [
  ["revisar", /^(revis\w+|analis\w+|avali\w+)\s+(este|esse|o|a)\s+(diff|patch|trecho|pull request|codigo abaixo|codigo a seguir)\b[\s\S]*$/],
  ["anotar_projeto", /^anot\w*\s+(no|na|ao|em)\s+(projeto\s+)?.+?\s+que\s+.+$/],
  ["ficha", /^(ficha|anotacoes)\s+(do\s+)?projeto\s+.+$/],
  ["projetos", /^(meus projetos|quais (sao )?(os )?(meus )?projetos|lista\w*\s+(os\s+)?(meus\s+)?projetos)$/],
  ["perfil", /^((meu|minha)\s+(stack|nivel|modalidade|ingles|cidade)\s*(e|eh|sao|:|=)\s*.+|(quero\s+)?evit\w+\s+.+)$/],
  ["vagas", /^((tem|ha|existe\w*|quero|ver|mostr\w*|me mostr\w*|procur\w*|busc\w*|busqu\w*|lista\w*|quais)\b.{0,25}\bvagas?\b|vagas?\b)/],
  ["habilidades", /^(quais (sao )?(as )?(minhas |suas )?habilidades.*|minhas habilidades|suas habilidades|habilidades de programador.*|que habilidades.*|lista de habilidades)$/],
  ["evoluir", /^(o que (devo|eu devo|posso|preciso) (estudar|evoluir|melhorar|praticar).*|qual (e )?(a )?(minha |sua )?proxima habilidade.*|proxima habilidade.*|(qual (e )?(o )?|me de (o )?)?treino (da|de) semana.*|como (evoluir|melhorar|praticar)( como programador| minhas habilidades)?.*|plano de (estudo|evolucao).*)$/],
  ["checklist", /^(checklist|lista de verificacao)\s+.+$/],
  ["recomendar", /^(qual|que|quais)\s+(stack|tecnologia|tecnologias|linguagem|linguagens|framework|frameworks|banco|bancos)\b.*|^(recomend\w+|sugir\w+|indic\w+)\s+(uma?\s+)?(stack|tecnologia|linguagem|framework)\b.*|^(o que|qual)\s+(devo|eu devo|posso)\s+usar\b.*/],
  ["clima", /\b(clima|previsao do tempo|vai chover|temperatura)\b/],
  ["noticias", /\bnoticias?\b/],
];

const pastaDe = (nome) => `Projetos/${nome.trim()}/Sobre`;

const HANDLERS = {
  _revisar(texto) {
    const corpo = texto.includes("\n") ? texto.split("\n").slice(1).join("\n") : texto.includes(":") ? texto.split(":").slice(1).join(":") : "";
    return corpo.trim() ? relatorioRevisao(corpo) : 'Cole o diff ou o código depois do pedido: escreva "revise este diff" e, na linha seguinte, o conteúdo.';
  },

  async _anotar_projeto(texto) {
    const m = /^\s*anot\w*\s+(?:no|na|ao|em)\s+(?:projeto\s+)?(.+?)\s+que\s+(.+)$/i.exec(texto.trim());
    if (!m) return 'Diga assim: "anota no projeto Loja que o banco é PostgreSQL".';
    const ref = pastaDe(m[1]);
    const atual = (await this.memoria.ler(ref))?.corpo || `# ${m[1].trim()}\n`;
    await this.memoria.guardar(ref, `${atual.trimEnd()}\n- ${m[2].trim()}\n`, "projeto", m[1].trim());
    return `Anotado no projeto **${m[1].trim()}**: ${m[2].trim()}`;
  },

  async _ficha(texto) {
    const nome = texto.replace(/^\s*(ficha|anotacoes|anotações)\s+(do\s+)?projeto\s+/i, "").trim();
    const nota = (await this.memoria.listar("Projetos/")).find((n) => fold(n.ref).includes(fold(nome)));
    return nota ? `**Ficha do projeto ${nota.titulo}**\n${nota.corpo}` : `Não tenho ficha do projeto "${nome}". Diga "anota no projeto ${nome} que ..." para começar.`;
  },

  async _projetos() {
    const nomes = [...new Set((await this.memoria.listar("Projetos/")).map((n) => n.ref.split("/")[1]))];
    return nomes.length ? "**Seus projetos:** " + nomes.join(", ") + '. Peça "ficha do projeto <nome>".' : 'Nenhum projeto ainda. Diga "anota no projeto Loja que ..." para criar.';
  },

  async _perfil(texto) { return (await atualizarPerfil(this.memoria, texto)) || "Não entendi o que anotar."; },
  async _vagas() { return vagas(this.memoria, this.buscar); },
  _habilidades() { return this.habil.visaoGeral(); },
  _evoluir(texto) { return /plano|estudo|evolu/.test(fold(texto)) && !/semana|proxima|devo/.test(fold(texto)) ? this.habil.plano(texto.replace(/^.*?(?:em|de|para)\s+/i, "")) : this.habil.treinoDaSemana(this.agora()); },
  _checklist(texto) { return this.habil.checklist(texto.replace(/^\s*(checklist|lista de verifica\S+)\s+(de|do|da|para)?\s*/i, "")); },
  _recomendar(texto) {
    const achadas = [...fold(texto).matchAll(/(front[\s-]?end|back[\s-]?end|full[\s-]?stack|mobile|celular|bancos? de dados?|linguagens?|stacks?)/g)].map((m) => m[1].replace(/\s+/g, " "));
    // "linguagens para back end": a área específica (front/back/full/mobile) vale mais que a palavra genérica
    const area = achadas.find((a) => /^(front|back|full|mobile|celular)/.test(a)) || achadas[0];
    return area && !/\b(loja|gestao|dashboard|chat|blog|api|site|erp|estoque)\b/.test(fold(texto)) ? this.stack.visaoGeral(area) : this.stack.recomendar(texto);
  },

  async _clima(texto) {
    const m = /\b(?:em|de|no|na)\s+([^?!.]+)$/i.exec(texto.replace(/^.*?\b(clima|previs[ãa]o do tempo|vai chover|temperatura)\b/i, "$1"));
    const cidade = (m && m[1].trim()) || (await this.memoria.meta("cidade")) || "";
    try { return await clima(cidade, this.buscar); } catch (e) { return `Não consegui ver o clima agora (${e.message}).`; }
  },

  async _noticias(texto) { return noticias(/tecnolog|tech|programa|dev/.test(fold(texto)) ? "tecnologia" : "gerais", 5, this.buscar); },
};

export function instalarExtras(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}

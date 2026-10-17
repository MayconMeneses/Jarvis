// Conhecimento curado (o mesmo do PC): tópicos de lógica, engenharia e UX, tecnologias, algoritmos e padrões de projeto.
import { escaparRegex, fold } from "./util.js";

const NOMES_LINGUAGEM = { python: "Python", javascript: "JavaScript", go: "Go", java: "Java", csharp: "C#" };
const APELIDOS = { py: "python", js: "javascript", node: "javascript", nodejs: "javascript", golang: "go", "c#": "csharp", dotnet: "csharp" };

// Cada nome vira uma expressão regular uma única vez: no celular, recompilar centenas delas a cada pergunta deixava o app lento.
const _regex = new Map();
function palavra(nome) {
  if (!_regex.has(nome)) _regex.set(nome, new RegExp(`(?<![\\p{L}\\p{N}_])${escaparRegex(nome)}(?![\\p{L}\\p{N}_])`, "u"));
  return _regex.get(nome);
}
// Teste barato primeiro (includes): só os nomes que aparecem no texto chegam a compilar a expressão regular.
const achaPalavra = (nome, texto) => (texto.includes(nome) ? palavra(nome).exec(texto) : null);

export class Saber {
  constructor(dados) {
    this.topicos = dados.topicos || [];
    this.tecnologias = dados.tecnologias || [];
    this.algoritmos = dados.algoritmos || [];
    this.padroes = dados.padroes || [];
    this.estruturas = dados.estruturas || [];
    this.tipos = dados.tipos || [];
    this.habilidades = dados.habilidades || [];
  }

  static nomes(item) { return new Set([fold(item.id), fold(item.nome), ...(item.aliases || []).map(fold)]); }

  static achar(itens, termo) {
    const limpo = fold(termo).trim().replace(/[?!.]+$/g, "").replace(/^(a|o|as|os|um|uma)\s+/, "");
    return itens.find((i) => [fold(i.id), fold(i.nome)].includes(limpo)) || itens.find((i) => (i.aliases || []).map(fold).includes(limpo)) || null;
  }

  // Itens citados no texto (palavra inteira), na ordem em que aparecem; no empate, o nome mais longo.
  static citados(itens, texto) {
    const baixo = fold(texto), achados = [];
    for (const item of itens) {
      const casos = [...Saber.nomes(item)].map((n) => {
        const m = achaPalavra(n, baixo);
        return m ? [m.index, -n.length] : null;
      }).filter(Boolean);
      if (casos.length) achados.push([casos.sort((a, b) => a[0] - b[0] || a[1] - b[1])[0], item]);
    }
    return achados.sort((a, b) => a[0][0] - b[0][0] || a[0][1] - b[0][1]).map(([, i]) => i);
  }

  topico(termo) { return Saber.achar(this.topicos, termo); }
  tecnologia(termo) { return Saber.achar(this.tecnologias, termo); }
  padrao(texto) { return Saber.maisLongo([...this.padroes], texto); }
  // Algoritmos e estruturas de dados (pilha, fila, árvore...) são buscados juntos: "como implementar uma trie".
  algoritmo(texto) { return Saber.maisLongo([...this.algoritmos, ...this.estruturas], texto); }

  static maisLongo(itens, texto) {
    const baixo = fold(texto);
    let melhor = null, tamanho = 0;
    for (const item of itens) {
      for (const bruto of [item.nome, item.id.replace(/_/g, " "), ...(item.aliases || [])]) {
        const n = fold(bruto);
        if (n.length > tamanho && achaPalavra(n, baixo)) { melhor = item; tamanho = n.length; }
      }
    }
    return melhor;
  }

  // Tópicos citados: engenharia e UX antes dos conceitos gerais de lógica (mais específicos).
  citadosTopicos(texto) {
    const ordem = { engenharia: 0, ux: 1, logica: 2 };
    return Saber.citados(this.topicos, texto).sort((a, b) => ordem[a.area] - ordem[b.area]);
  }

  linguagem(texto, padrao = "python") {
    const baixo = fold(texto);
    let primeiro = baixo.length + 1, achada = padrao;
    for (const nome of [...Object.keys(NOMES_LINGUAGEM), ...Object.keys(APELIDOS)]) {
      const m = new RegExp(`(?<![\\w#.])${escaparRegex(nome)}(?![\\w#])`).exec(baixo);
      if (m && m.index < primeiro) { primeiro = m.index; achada = APELIDOS[nome] || nome; }
    }
    return achada;
  }

  descrever(t) {
    return [`**${t.nome}**`, t.resumo, "", "**Como aplicar:**", ...t.passos.map((p) => `- ${p}`), "", `**Analogia:** ${t.analogia}`, "",
      "**Exemplo:**", "```", t.exemplo, "```", `**Erros comuns:** ${t.erros.join("; ")}`, `**Para praticar:** ${t.exercicios.join(" · ")}`].join("\n");
  }

  descreverTecnologia(t) {
    const lista = (x) => (x || []).map((i) => `- ${i}`).join("\n");
    return [`**${t.nome}**`, t.resumo, "", "**Bom para:**", lista(t.usos), "", "**Pontos fortes:**", lista(t.fortes), "", "**Cuidados:**", lista(t.fracos),
      t.curva ? `\n**Curva de aprendizado:** ${t.curva}` : ""].join("\n");
  }

  comparar(a, b) {
    return `**${a.nome} × ${b.nome}**\n- **${a.nome}:** ${a.resumo}\n${a.analogia ? `  - Analogia: ${a.analogia}\n` : ""}- **${b.nome}:** ${b.resumo}\n${b.analogia ? `  - Analogia: ${b.analogia}\n` : ""}`
      + (a.erros && b.erros ? `- **Erros comuns** — ${a.nome}: ${a.erros.join("; ")} | ${b.nome}: ${b.erros.join("; ")}` : "");
  }

  mostrar(item, lang = "python") {
    lang = APELIDOS[lang] || lang;
    const saida = [`**${item.nome}**`, item.problema, ...(item.complexidade ? [`- **Complexidade:** ${item.complexidade}`] : []), "", "**Ideia:**",
      ...item.ideia.map((p) => `- ${p}`), "", "**Pseudocódigo:**", "```", item.pseudocodigo, "```"];
    const codigo = item.codigo[lang];
    if (codigo === undefined) return saida.join("\n") + `\n\nTenho este item em: ${Object.keys(item.codigo).map((l) => NOMES_LINGUAGEM[l] || l).join(", ")}.`;
    saida.push("", `**Em ${NOMES_LINGUAGEM[lang] || lang}:**`, "```" + lang, codigo, "```");
    return saida.join("\n");
  }

  resumo() {
    const linhas = (titulo, itens) => `**${titulo}**\n` + itens.map((i) => `- **${i.nome}**: ${(i.resumo || i.problema).split(". ")[0].replace(/\.$/, "")}.`).join("\n");
    return [linhas("Conceitos e tópicos que eu explico:", this.topicos), linhas("Padrões de projeto:", this.padroes), linhas("Estruturas de dados:", this.estruturas),
      linhas("Algoritmos:", this.algoritmos)].join("\n\n");
  }

  // Explica o que a Jarvis souber sobre o termo, ou null.
  explicar(termo, lang = "python") {
    const t = this.topico(termo) || this.citadosTopicos(termo)[0];
    if (t) return this.descrever(t);
    const p = this.padrao(termo);
    if (p) return this.mostrar(p, lang);
    const a = this.algoritmo(termo);
    if (a) return this.mostrar(a, lang);
    const tec = this.tecnologia(termo) || Saber.citados(this.tecnologias, termo)[0];
    return tec ? this.descreverTecnologia(tec) : null;
  }
}

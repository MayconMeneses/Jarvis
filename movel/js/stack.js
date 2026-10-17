// Tecnologias (linguagens, front, back, bancos, stacks) e recomendação de stack por tipo de sistema: a mesma base do PC.
import { escaparRegex, fold } from "./util.js";

const AREAS = { front: "front-end", back: "back-end", full: "full stack", mobile: "mobile" };
const CATEGORIAS = { linguagem: "Linguagens", front: "Front-end", back: "Back-end", banco: "Bancos de dados", stack: "Stacks full stack", full: "Full stack", mobile: "Mobile" };
const ALIASES = { "front end": "front", frontend: "front", "front-end": "front", "back end": "back", backend: "back", "back-end": "back", "full stack": "full", fullstack: "full",
  "full-stack": "full", "banco de dados": "banco", bancos: "banco", "bancos de dados": "banco", linguagens: "linguagem", stacks: "stack", celular: "mobile" };

export class Stack {
  constructor(tecnologias, tipos) { this.tecnologias = tecnologias || []; this.tipos = tipos || []; }

  porArea(area) {
    area = ALIASES[fold(area)] || fold(area);
    if (["banco", "linguagem", "stack"].includes(area)) return this.tecnologias.filter((e) => e.categoria === area);
    return this.tecnologias.filter((e) => (e.areas || []).includes(area) && e.categoria !== "banco");
  }

  descrever(e) {
    return `**${e.nome}** (${CATEGORIAS[e.categoria] || e.categoria}): ${e.resumo}\n- **Usos:** ${e.usos.join("; ")}\n- **Pontos fortes:** ${e.fortes.join("; ")}\n`
      + `- **Pontos fracos:** ${e.fracos.join("; ")}\n- **Quando escolher:** ${e.quando.join("; ")}\n- **Curva de aprendizado:** ${e.curva}\n`
      + `- **Como começar:** ${e.comeco.map((c) => "`" + c + "`").join(" → ")}`;
  }

  visaoGeral(area) {
    const itens = this.porArea(area);
    if (!itens.length) return "Não conheço essa área. Pergunte por front end, back end, full stack, mobile, bancos de dados ou linguagens.";
    const titulo = AREAS[fold(area)] || CATEGORIAS[fold(area)] || area;  // igual ao PC: usa o nome como foi pedido
    return `**${titulo[0].toUpperCase() + titulo.slice(1).toLowerCase()}: o que eu conheço**\n` + itens.map((e) => `- **${e.nome}**: ${e.resumo}`).join("\n")
      + '\n\nPergunte "o que é <nome>", "compare <A> e <B>" ou "qual stack para <tipo de sistema>".';
  }

  comparar(a, b) {
    const linha = (rotulo, chave) => `- **${rotulo}** — ${a.nome}: ${a[chave].join("; ")} | ${b.nome}: ${b[chave].join("; ")}`;
    return `**${a.nome} × ${b.nome}**\n- **O que é** — ${a.nome}: ${a.resumo} | ${b.nome}: ${b.resumo}\n${linha("Pontos fortes", "fortes")}\n${linha("Pontos fracos", "fracos")}\n`
      + `${linha("Quando escolher", "quando")}\n- **Curva** — ${a.nome}: ${a.curva} | ${b.nome}: ${b.curva}\n`
      + "Se a pergunta for de qual é melhor: depende do projeto; diga o tipo de sistema e eu recomendo uma stack.";
  }

  tipoDe(descricao) {
    const texto = fold(descricao);
    let melhor = null, pontos = 0;
    for (const tipo of this.tipos) {
      let p = 0;
      for (const palavra of tipo.palavras) if (new RegExp(`(?<![\\p{L}\\p{N}_])${escaparRegex(fold(palavra))}(?![\\p{L}\\p{N}_])`, "u").test(texto)) p += 1 + palavra.split(" ").length;
      if (p > pontos) { melhor = tipo; pontos = p; }
    }
    return melhor;
  }

  visaoTipos() { return "**Tipos de sistema que sei recomendar:** " + this.tipos.map((t) => t.nome).join(", ") + "."; }

  recomendar(descricao) {
    const tipo = this.tipoDe(descricao);
    if (!tipo) {
      return 'Não entendi que tipo de sistema é. Diga, por exemplo, "loja virtual", "sistema de gestão", "API", "dashboard", "aplicativo de celular", "chat em tempo real" ou "site institucional".\n' + this.visaoTipos();
    }
    const nomes = (ids) => ids.map((i) => this.tecnologias.find((t) => t.id === i)?.nome).filter(Boolean).join(", ");
    const linhas = [`**Para ${tipo.nome.toLowerCase()}, eu recomendo:**`];
    for (const [rotulo, chave] of [["Front-end", "front"], ["Back-end", "back"], ["Banco de dados", "banco"]]) if (tipo[chave].length) linhas.push(`- **${rotulo}:** ${nomes(tipo[chave])}`);
    linhas.push(`- **Por quê:** ${tipo.motivo}`);
    if (tipo.alternativas.length) linhas.push("- **Alternativas:** " + tipo.alternativas.join("; "));
    if (tipo.modelo) linhas.push(`\nPosso montar os arquivos de um projeto inicial pronto (modelo \`${tipo.modelo}\`) na aba Oficina, para você baixar em ZIP.`);
    return linhas.join("\n");
  }
}

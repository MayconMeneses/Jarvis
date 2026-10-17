// Habilidades de programador (as mesmas 23 do PC): o que dominar, checklist, plano de evolução e o treino da semana.
// No celular não há pasta de projeto para avaliar; a revisão é do trecho que você colar (veja revisao.js).
import { fold, semanaIso } from "./util.js";

const NIVEIS = ["iniciante", "intermediário", "avançado"];

export class Habilidades {
  constructor(catalogo, saber) { this.catalogo = catalogo || []; this.saber = saber; }

  achar(termo) {
    const baixo = fold(termo).trim().replace(/[ ?!.]+$/g, "");
    const exata = this.catalogo.find((h) => [fold(h.id), fold(h.nome)].includes(baixo));
    if (exata) return exata;
    return this.catalogo.find((h) => baixo && (fold(h.nome).includes(baixo) || baixo.split(/\s+/).includes(fold(h.id)))) || null;
  }

  visaoGeral() {
    return "**Habilidades de programador que eu acompanho:**\n" + this.catalogo.map((h) => `- **${h.nome}**: ${h.resumo}`).join("\n");
  }

  checklist(termo) {
    const h = this.achar(termo);
    if (!h) return "Não conheço esse aspecto. " + this.visaoGeral();
    return [`**Checklist: ${h.nome}**`, h.resumo, "", "**Práticas para conferir:**", ...h.praticas.map((p) => `- [ ] ${p}`), "", "**Níveis:**",
      ...h.niveis.map((n, i) => `- ${NIVEIS[i]}: ${n}`)].join("\n");
  }

  plano(termo) {
    const h = this.achar(termo);
    if (!h) return "Diga qual habilidade quer evoluir. " + this.visaoGeral();
    const estudar = h.estudar.map((ref) => (this.saber.topico(ref) || this.saber.tecnologia(ref) || this.saber.padrao(ref) || this.saber.algoritmo(ref))).filter(Boolean).map((i) => i.nome);
    return `**Plano para evoluir: ${h.nome}**\n1. Releia o checklist (peça "checklist de ${h.nome.toLowerCase()}") e marque o que você já faz.\n`
      + `2. Estude (peça "explique <tema>"): ${estudar.join(", ") || "prática direta"}.\n3. **Treino da semana:** ${h.treino}\n`
      + '4. Depois, cole um código seu ("revise este trecho") e confira se os pontos melhoraram.';
  }

  // Uma habilidade por semana, em rodízio por todas: a prática pequena e constante que faz evoluir sempre.
  treinoDaSemana(hoje = new Date()) {
    const [, semana] = semanaIso(hoje);
    const h = this.catalogo[semana % this.catalogo.length];
    return `**Treino da semana: ${h.nome}**\n\n` + this.plano(h.id);
  }
}

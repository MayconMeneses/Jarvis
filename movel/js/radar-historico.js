// Histórico do Radar neste aparelho (meta "radar:hist" e "radar:cfg"): o que já foi visto, títulos recentes (ineditismo) e a última execução.
// Guarda só título, fonte e data; nunca o corpo do artigo. Fica só 14 dias (o PC guarda 90): o celular tem pouco espaço.
import { idDoArtigo } from "./radar-dedup.js";

export const RETENCAO_DIAS = 14;
export const MAX_ARTIGOS = 1500;
const CFG_PADRAO = { nicho: "", usarIa: false };

export class Historico {
  constructor(memoria, agora = () => Date.now() / 1000) { Object.assign(this, { memoria, agora, d: { artigos: {}, ultima: null } }); }

  async carregar() {
    const d = await this.memoria.meta("radar:hist");
    this.d = d && typeof d === "object" && d.artigos ? d : { artigos: {}, ultima: null };
    return this;
  }
  salvar() { return this.memoria.definirMeta("radar:hist", this.d); }

  async config() { return { ...CFG_PADRAO, ...((await this.memoria.meta("radar:cfg")) || {}) }; }
  async definirConfig(parcial) { const c = { ...(await this.config()), ...parcial }; await this.memoria.definirMeta("radar:cfg", c); return c; }

  jaVisto(artigo) { return idDoArtigo(artigo) in this.d.artigos; }
  titulosRecentes(dias = RETENCAO_DIAS) { const corte = this.agora() - dias * 86400; return Object.values(this.d.artigos).filter((a) => a.v >= corte).map((a) => a.t); }

  // Grava o que foi visto. Devolve quantos eram novos.
  registrar(artigos, escolhidos = new Set()) {
    let novos = 0;
    for (const a of artigos) {
      const id = idDoArtigo(a);
      if (!(id in this.d.artigos)) { novos++; this.d.artigos[id] = { t: a.titulo, f: a.fonte, v: this.agora(), e: 0 }; }
      if (escolhidos.has(id)) this.d.artigos[id].e = 1;
    }
    return novos;
  }

  limpar(dias = RETENCAO_DIAS) {
    const corte = this.agora() - dias * 86400;
    let ids = Object.entries(this.d.artigos);
    ids = ids.filter(([, a]) => a.v >= corte).sort((a, b) => b[1].v - a[1].v).slice(0, MAX_ARTIGOS);
    this.d.artigos = Object.fromEntries(ids);
  }

  registrarExecucao(dia, varridos, novos, escolhidos, falhas, resultado) {
    this.d.ultima = { dia, quando: this.agora(), varridos, novos, escolhidos, falhas: falhas.join("; ").slice(0, 600), resultado };
  }
}

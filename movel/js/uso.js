// Uso de IA no celular: contadores LOCAIS por fonte (chaves de nuvem e cérebro do aparelho). Guarda só números (chamadas e tokens), nunca chaves nem textos.
// Dados em meta "uso:AAAA-MM" = { "AAAA-MM-DD": { <fonte>: { c: chamadas, e: tokens de entrada, s: tokens de saída, x: chamadas com tokens estimados } } }.
import { isoData } from "./util.js";

export const FONTES = {
  gemini: "Google Gemini", nvidia: "NVIDIA", brave: "Brave Search", openai: "OpenAI", groq: "Groq", openrouter: "OpenRouter",
  personalizado: "Outro provedor", aparelho: "Cérebro do aparelho",
};
// US$ por 1 milhão de tokens (e / s) e por chamada (c). Valores de partida: CONFIRA nos sites dos provedores e edite no painel.
export const PRECOS_PADRAO = {
  gemini: { e: 0.3, s: 2.5, c: 0 }, nvidia: { e: 0, s: 0, c: 0 }, brave: { e: 0, s: 0, c: 0.005 }, openai: { e: 0.15, s: 0.6, c: 0 },
  groq: { e: 0.59, s: 0.79, c: 0 }, openrouter: { e: 0, s: 0, c: 0 }, personalizado: { e: 0, s: 0, c: 0 },
  referencia: { e: 0.15, s: 0.6, c: 0 },  // quanto custaria na nuvem: base do "economizado" do cérebro do aparelho
};
const ID = /^[a-z0-9_-]{1,30}$/;
const positivo = (v, max = 1e9) => { const n = Number(v); return Number.isFinite(n) && n >= 0 ? Math.min(n, max) : 0; };

export const estimarTokens = (texto) => Math.ceil(String(texto ?? "").length / 4);
export const mensagensParaTexto = (mensagens) => (mensagens || []).map((m) => m.content).join("\n");

// Custo em US$ de uma linha { c, e, s } com a tabela de preços da fonte.
export function custoDe(linha, preco) {
  if (!preco) return 0;
  return (linha.e / 1e6) * preco.e + (linha.s / 1e6) * preco.s + linha.c * preco.c;
}

const zero = () => ({ c: 0, e: 0, s: 0, x: 0 });
const somar = (a, b) => ({ c: a.c + b.c, e: a.e + b.e, s: a.s + b.s, x: a.x + b.x });

export class Uso {
  constructor(memoria, relogio = () => new Date()) { this.memoria = memoria; this.relogio = relogio; }

  async config() {
    const salvo = (await this.memoria.meta("uso:config")) || {};
    return { orcamento: positivo(salvo.orcamento), alerta: Math.min(100, positivo(salvo.alerta ?? 80)) || 80, precos: { ...PRECOS_PADRAO, ...(salvo.precos || {}) } };
  }
  async definirConfig(parcial) { await this.memoria.definirMeta("uso:config", { ...(await this.config()), ...parcial }); }

  // Registra uma chamada. Sem número de tokens vindo do provedor, estima pelo tamanho do texto (4 caracteres por token) e marca como estimado.
  async registrar(fonte, { entrada = null, saida = null, textoEntrada = "", textoSaida = "", quando = this.relogio() } = {}) {
    if (!ID.test(fonte)) return;
    const busca = fonte === "brave", estimado = !busca && !(Number.isFinite(entrada) && Number.isFinite(saida));
    const e = busca ? 0 : Number.isFinite(entrada) ? entrada : estimarTokens(textoEntrada);
    const s = busca ? 0 : Number.isFinite(saida) ? saida : estimarTokens(textoSaida);
    const chave = "uso:" + isoData(quando).slice(0, 7), mes = (await this.memoria.meta(chave)) || {};
    const dia = (mes[isoData(quando)] ||= {});
    dia[fonte] = somar(dia[fonte] || zero(), { c: 1, e, s, x: estimado ? 1 : 0 });
    await this.memoria.definirMeta(chave, mes);
  }

  async mes(quando = this.relogio()) { return (await this.memoria.meta("uso:" + isoData(quando).slice(0, 7))) || {}; }

  // Resumo do mês: total por fonte, custo estimado em US$, economizado (cérebro do aparelho) e uso do orçamento.
  async resumo(quando = this.relogio()) {
    const cfg = await this.config(), porFonte = {};
    for (const dia of Object.values(await this.mes(quando))) for (const [f, l] of Object.entries(dia)) porFonte[f] = somar(porFonte[f] || zero(), l);
    let gasto = 0, economizado = 0;
    const fontes = Object.entries(porFonte).map(([id, l]) => {
      const aparelho = id === "aparelho", custo = aparelho ? 0 : custoDe(l, cfg.precos[id]);
      if (aparelho) economizado += custoDe(l, cfg.precos.referencia); else gasto += custo;
      return { id, nome: FONTES[id] || id, ...l, custo };
    }).sort((a, b) => b.custo - a.custo || b.c - a.c);
    const pct = cfg.orcamento > 0 ? (100 * gasto) / cfg.orcamento : null;
    return { fontes, gasto, economizado, orcamento: cfg.orcamento, pct, alerta: pct !== null && pct >= cfg.alerta };
  }

  // Custo por dia (para o gráfico). Dias sem uso valem 0.
  async serieDiaria(dias = 30, quando = this.relogio()) {
    const cfg = await this.config(), saida = [];
    for (let i = dias - 1; i >= 0; i--) {
      const d = new Date(quando.getFullYear(), quando.getMonth(), quando.getDate() - i), dia = (await this.mes(d))[isoData(d)] || {};
      let custo = 0, tokens = 0;
      for (const [f, l] of Object.entries(dia)) { tokens += l.e + l.s; if (f !== "aparelho") custo += custoDe(l, cfg.precos[f]); }
      saida.push({ dia: isoData(d), custo, tokens });
    }
    return saida;
  }

  // Cópia em JSON: só contadores, preços e orçamento. Nunca chaves.
  async exportar() {
    const meses = {};
    for (const c of (await this.memoria.armazem.chaves()).filter((k) => /^meta:uso:\d{4}-\d{2}$/.test(k))) meses[c.slice(9)] = await this.memoria.armazem.ler(c);
    return JSON.stringify({ formato: "jarvis-uso-1", config: await this.config(), meses }, null, 1);
  }

  async importar(texto) {
    const d = JSON.parse(texto);
    if (d.formato !== "jarvis-uso-1" || typeof d.meses !== "object" || !d.meses) throw new Error("arquivo de uso inválido");
    let n = 0;
    for (const [mes, dias] of Object.entries(d.meses)) {
      if (!/^\d{4}-\d{2}$/.test(mes) || typeof dias !== "object" || !dias) continue;
      const limpo = {};
      for (const [dia, fontes] of Object.entries(dias)) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(dia) || typeof fontes !== "object" || !fontes) continue;
        for (const [f, l] of Object.entries(fontes)) {
          if (!ID.test(f) || !l || typeof l !== "object") continue;
          (limpo[dia] ||= {})[f] = { c: positivo(l.c), e: positivo(l.e), s: positivo(l.s), x: positivo(l.x) };
          n++;
        }
      }
      await this.memoria.definirMeta("uso:" + mes, limpo);
    }
    const cfg = d.config || {}, precos = {};
    for (const [f, p] of Object.entries(cfg.precos || {})) if (ID.test(f) && p && typeof p === "object") precos[f] = { e: positivo(p.e, 1e4), s: positivo(p.s, 1e4), c: positivo(p.c, 1e4) };
    await this.definirConfig({ orcamento: positivo(cfg.orcamento), alerta: Math.min(100, positivo(cfg.alerta ?? 80)) || 80, precos: { ...(await this.config()).precos, ...precos } });
    return n;
  }

  async relatorio() {
    const r = await this.resumo(), usd = (v) => "US$ " + v.toFixed(2).replace(".", ",");
    if (!r.fontes.length) return "Ainda não registrei nenhuma chamada de IA neste mês. Os contadores ficam só neste aparelho (painel Uso de IA, na aba Cérebro).";
    const linhas = r.fontes.map((f) => `- **${f.nome}**: ${f.c} chamada(s)${f.id === "brave" ? "" : `, ${f.e + f.s} tokens${f.x ? " (alguns estimados)" : ""}`} — ${f.id === "aparelho" ? "custo zero" : usd(f.custo)}`);
    let t = `**Uso de IA neste mês** (estimativa; preços a conferir):\n${linhas.join("\n")}\n\nGasto estimado: **${usd(r.gasto)}**.`;
    if (r.economizado > 0) t += ` O cérebro do aparelho economizou cerca de ${usd(r.economizado)}.`;
    if (r.pct !== null) t += ` Orçamento: ${r.pct.toFixed(0)}% de ${usd(r.orcamento)}${r.alerta ? " — atenção, passou do alerta" : ""}.`;
    return t;
  }
}

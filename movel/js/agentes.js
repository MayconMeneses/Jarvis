// Painel de Agentes (mínimo): estado dos processos do app a partir de batimentos gravados em meta ("agente:<id>:ultimo" e "agente:<id>:estado").
// O celular só roda com o app ABERTO; por isso "app estava fechado" é um estado próprio e neutro (não é erro).
export const MINUTO = 60 * 1000, DIA = 24 * 60 * MINUTO;
export const AGENTES = [
  { id: "proativo", nome: "Avisos ao abrir", cadenciaMs: null, nota: "roda cada vez que o app abre" },
  { id: "aprender", nome: "Aprender sozinha", cadenciaMs: MINUTO, nota: "confere a cada minuto; estuda com o app parado por 10 min" },
  { id: "avaliacao", nome: "Avaliação semanal do cérebro", cadenciaMs: 7 * DIA, nota: "uma vez por semana, com o app aberto e parado" },
  { id: "cerebro", nome: "Cérebro do aparelho", cadenciaMs: null, nota: "responde quando você pergunta" },
  { id: "oficina", nome: "Oficina (rodar e testar)", cadenciaMs: null, nota: "roda quando você toca em Rodar ou Testar" },
];
export const ROTULOS = { ok: "OK", atrasado: "Atrasado", erro: "Erro", ocioso: "Ocioso", desligado: "Desligado", fechado: "App estava fechado" };
export const LIMITE_ATRASO = 2.5;  // atrasado = sem batimento por mais de 2,5 ciclos

// Decide o estado. `ultimo` e `inicioSessao` são ms (ultimo null = nunca rodou). Ordem: desligado, nunca rodou, app fechado, erro, atrasado, ocioso, ok.
export function decidir({ agora, ultimo, estado = "ok", cadenciaMs = null, ligado = true, inicioSessao = 0 }) {
  if (!ligado) return "desligado";
  if (ultimo === null || ultimo === undefined) return "ocioso";
  if (cadenciaMs && cadenciaMs <= 60 * MINUTO && ultimo < inicioSessao) return "fechado";
  if (estado === "erro") return "erro";
  if (cadenciaMs && Math.max(0, agora - ultimo) > LIMITE_ATRASO * cadenciaMs) return "atrasado";
  return estado === "ocioso" ? "ocioso" : "ok";
}

export function haQuanto(ms) {
  const m = Math.floor(Math.max(0, ms) / MINUTO);
  return m < 1 ? "agora há pouco" : m < 60 ? `há ${m} min` : m < 48 * 60 ? `há ${Math.floor(m / 60)} h` : `há ${Math.floor(m / 1440)} dias`;
}

export class Agentes {
  constructor(memoria, relogio = () => Date.now()) { this.memoria = memoria; this.relogio = relogio; this.inicio = relogio(); }

  // Grava o batimento. Nunca lança: o painel não pode derrubar quem está trabalhando.
  async marcar(id, estado = "ok") {
    try {
      await this.memoria.definirMeta(`agente:${id}:ultimo`, new Date(this.relogio()).toISOString());
      await this.memoria.definirMeta(`agente:${id}:estado`, estado);
    } catch { /* sem armazenamento: o painel mostra "nunca rodou" */ }
  }

  async ler(id) {
    const iso = await this.memoria.meta(`agente:${id}:ultimo`), t = iso ? Date.parse(iso) : NaN;
    return { ultimo: Number.isFinite(t) ? t : null, estado: (await this.memoria.meta(`agente:${id}:estado`)) || "ok" };
  }

  // ctx.ligados[id] (padrão true) e ctx.ultimos[id] (ms, substitui o batimento) vêm de quem conhece o processo.
  async todos(ctx = {}) {
    const agora = this.relogio(), saida = [];
    for (const a of AGENTES) {
      const { ultimo: gravado, estado } = await this.ler(a.id), ultimo = ctx.ultimos?.[a.id] ?? gravado;
      const situacao = decidir({ agora, ultimo, estado, cadenciaMs: a.cadenciaMs, ligado: ctx.ligados?.[a.id] !== false, inicioSessao: this.inicio });
      saida.push({ ...a, situacao, rotulo: ROTULOS[situacao], quando: ultimo === null || ultimo === undefined ? "ainda não rodou" : haQuanto(agora - ultimo) });
    }
    return saida;
  }
}

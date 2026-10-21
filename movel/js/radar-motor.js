// Pedidos de chat do Radar, das notícias e do "Ler para mim": "radar", "ouvir radar", "notícias de tecnologia", "notícias de IA", "ler notícia 2", "parar".
// O objeto `noticiasCtx` (noticias-ctx.js) é ligado pelo main.js. Tudo que vem de feed é texto de terceiros: só vira texto na tela e voz, nunca ordem.
import { manchetes, porAssunto } from "./noticias-fontes.js";
import { sugerir } from "./radar-fontes.js";
import { markdown, paraTela } from "./radar-render.js";

const EXTRAS = [
  ["parar_leitura", /^(parar|pare|para|silencio|chega)( de ler| a leitura| leitura| de falar)?$/],
  ["continuar_leitura", /^(continuar|continue|retomar|retome)( a)?( leitura)?$/],
  ["ler_noticia", /^(ler|leia|le|ouvir|ouca)\s+(para mim\s+)?(a\s+)?(noticia|manchete|materia)\s+(\d{1,2})(\s+(completa|inteira|toda|no original))?$/],
  ["ouvir_radar", /^(ouvir|ouca|escutar|escute|tocar|toque|ler|leia)\s+(o\s+)?(radar|boletim)( de hoje)?$/],
  ["radar", /^radar(?!\s+(do|no)\s+pc$)(\s+.*)?$/],  // "radar do pc" é do PC pareado (motor-pc.js)
  ["noticias_tec", /^(ultimas\s+)?(noticias?|manchetes?)\s+(de\s+|sobre\s+)?(tecnologia|tech|programacao|ti)\b.*$/],
  ["noticias_assunto", /^(ultimas\s+)?(noticias?|manchetes?)\s+(de|sobre|do|da)\s+.{2,}$/],
];

const SEM_LISTA = 'Peça antes "notícias" ou "notícias de tecnologia" (ou abra a aba Notícias) para eu saber qual lista numerada ler.';
const SEM_CTX = "As notícias ainda não estão ligadas neste aparelho. Recarregue o app.";

// Lista numerada: "ler notícia 3" lê o terceiro. Link só como texto (o chat não cria links clicáveis).
export function formatarLista(titulo, itens, avisos) {
  if (!itens.length) return "Não consegui carregar notícias agora" + (avisos.length ? ` (${avisos.join("; ")})` : "") + ".";
  return `**${titulo}:**\n` + itens.map((n, i) => `${i + 1}. ${n.titulo} — ${n.fonte} ${n.link}`).join("\n")
    + (avisos.length ? `\n\n_Fora do ar: ${avisos.join("; ")}_` : "") + '\n\nDiga "ler notícia 1" para eu ler em voz alta.';
}

async function lista(ctx, tipo, titulo) {
  const { itens, avisos } = await manchetes(tipo, { buscar: ctx.buscar, proxy: ctx.proxy, limite: 6 });
  if (itens.length) ctx.noticias.ultima = itens;
  return formatarLista(titulo, itens, avisos);
}

async function subcomandoRadar(ctx, limpo, texto) {
  const r = ctx.radar, resto = limpo.replace(/^radar\s*/, "").trim();
  let m;
  if ((m = /^nicho\s+(.+)$/.exec(resto))) {
    const original = /nicho\s+(.+?)[\s.!?]*$/i.exec(texto);  // com os acentos que a pessoa escreveu
    const nicho = (await r.definirNicho(original ? original[1] : m[1])).nicho;
    return `Nicho do Radar: **${nicho}**. Diga "radar" para eu montar o boletim de hoje.`;
  }
  if ((m = /^ia\s+(ligar|ativar|sim|on|ligada)$/.exec(resto))) { await r.definirIa(true); return "Radar com IA ligado: um cérebro que você já cadastrou (aparelho ou nuvem) vai reescrever os resumos. Com a nuvem, o texto das notícias vai ao provedor."; }
  if ((m = /^ia\s+(desligar|desativar|nao|off|desligada)$/.exec(resto))) { await r.definirIa(false); return "Radar sem IA: só resumos extrativos, tudo neste aparelho."; }
  if (resto === "fontes") {
    const cfg = await r.config();
    const fontes = sugerir(cfg.nicho || "geral", await r.catalogo());
    return `**Fontes do Radar (${cfg.nicho || "geral"}):**\n` + fontes.map((f) => `- ${f.nome} (nota ${f.nota})`).join("\n");
  }
  if (resto === "ajuda") return 'Radar: "radar nicho inteligência artificial" define o assunto; "radar" mostra o boletim de hoje; "radar atualizar" busca de novo; "ouvir radar" lê em voz alta; "radar fontes"; "radar ia ligar" ou "radar ia desligar".';
  const atualizar = /^(atualizar|agora|novo|de novo)$/.test(resto);
  const hoje = atualizar ? null : await r.hoje();
  const res = hoje ? { ok: true, boletim: hoje } : await r.executar();
  if (!res.ok) return res.erro + (res.falhas?.length ? `\n\n_Detalhes: ${res.falhas.slice(0, 3).join("; ")}_` : "");
  return paraTela(markdown(res.boletim)) + '\n\nDiga "ouvir radar" para eu ler em voz alta.';
}

const contexto = (motor) => motor.noticiasCtx || (motor.__semCtx ||= { buscar: motor.buscar, proxy: null, noticias: { ultima: [] } });

const HANDLERS = {
  async _radar(texto, limpo) { return this.noticiasCtx ? subcomandoRadar(this.noticiasCtx, limpo, texto) : SEM_CTX; },

  async _ouvir_radar() {
    const ctx = this.noticiasCtx;
    if (!ctx) return SEM_CTX;
    if (!ctx.leitor.fala.disponivel()) return "Este navegador não tem voz para eu ler em voz alta.";
    const b = await ctx.radar.hoje();
    if (!b) return 'Ainda não montei o radar de hoje. Diga "radar nicho <assunto>" e depois "radar".';
    const plano = ctx.radar.roteiro(b);
    ctx.ouvirTexto(plano.texto, { depoisDaResposta: true });
    return `Lendo o radar de hoje (${plano.itens.length} notícias, cerca de ${Math.max(1, Math.round(plano.palavras / 180))} min). Diga "parar" para interromper.`;
  },

  // Sem o contexto das caixas (testes, app incompleto) as manchetes ainda funcionam, só sem o Worker.
  _noticias() { return lista(contexto(this), "gerais", "Manchetes (gerais)"); },
  _noticias_tec() { return lista(contexto(this), "tecnologia", "Manchetes (tecnologia)"); },

  async _noticias_assunto(texto, limpo) {
    const ctx = this.noticiasCtx;
    if (!ctx) return SEM_CTX;
    const assunto = limpo.replace(/^(ultimas\s+)?(noticias?|manchetes?)\s+(de|sobre|do|da)\s+/, "").trim();
    const { itens, avisos } = await porAssunto(assunto, { proxy: ctx.proxy });
    if (avisos.includes("sem Worker")) return `Notícias por assunto precisam do Worker do proxy (aba Cérebro), porque o Google News não libera o navegador. "notícias" e "notícias de tecnologia" funcionam sem ele.`;
    if (itens.length) ctx.noticias.ultima = itens;
    return formatarLista(`Notícias sobre ${assunto}`, itens, avisos);
  },

  async _ler_noticia(texto, limpo) {
    const ctx = this.noticiasCtx;
    if (!ctx) return SEM_CTX;
    const m = /(\d{1,2})(\s+(completa|inteira|toda|no original))?$/.exec(limpo), n = Number(m[1]), sufixo = m[3] || "";
    if (!ctx.noticias.ultima.length) return SEM_LISTA;
    const item = ctx.noticias.ultima[n - 1];
    if (!item) return `A lista tem ${ctx.noticias.ultima.length} notícias. Escolha de 1 a ${ctx.noticias.ultima.length}.`;
    if (!ctx.leitor.fala.disponivel()) return "Este navegador não tem voz para eu ler em voz alta.";
    const completo = sufixo !== "" && sufixo !== "no original";
    ctx.ouvir(item, { completo, original: sufixo === "no original", depoisDaResposta: true });
    return `Lendo a notícia ${n}: ${item.titulo} (${completo ? "artigo completo" : "só o trecho do feed"}). Diga "parar" para interromper.`;
  },

  async _parar_leitura() {
    const ctx = this.noticiasCtx;
    if (!ctx || !ctx.leitor.ocupado()) return "Não estou lendo nada agora.";
    ctx.leitor.parar();
    return 'Parei a leitura. Diga "continuar" para retomar de onde parei.';
  },

  async _continuar_leitura() {
    const ctx = this.noticiasCtx;
    if (!ctx || !ctx.leitor.estado().podeContinuar) return "Não tenho nenhuma leitura parada para continuar.";
    ctx.leitor.continuar();
    return "Continuando a leitura.";
  },
};

export function instalarRadar(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}


// Saída de voz da Jarvis: texto -> limpeza/normalização pt-BR -> frases (<= 350 caracteres) -> voz do aparelho (SpeechSynthesis) OU voz do Gemini.
// A voz do Gemini é opcional e sempre tem RESERVA: qualquer falha cai na voz do aparelho. Avisa a escuta quando começa/termina (anti-eco).
import { criarPlano, ligarFala } from "./orbe-voz.js";
import { escolherVoz } from "./voz-escolha.js";
import { MAX_TEXTO } from "./voz-gemini.js";
import { dividirParaFala, limparParaFala, pausaMs } from "./voz-texto.js";

// Quebra uma parte maior que `max` em pedaços, de preferência em espaço.
export function quebrar(parte, max = MAX_TEXTO) {
  const saida = [];
  for (let resto = parte.trim(); resto;) {
    if (resto.length <= max) { saida.push(resto); break; }
    let corte = resto.lastIndexOf(" ", max);
    if (corte < max / 2) corte = max;
    saida.push(resto.slice(0, corte).trim());
    resto = resto.slice(corte).trim();
  }
  return saida;
}
export const prepararPartes = (texto) => dividirParaFala(limparParaFala(String(texto ?? ""))).flatMap((p) => quebrar(p));

export class Saida {
  constructor({ sintese = globalThis.speechSynthesis, Fala = globalThis.SpeechSynthesisUtterance, esperar = (ms) => new Promise((r) => setTimeout(r, ms)) } = {}) {
    Object.assign(this, { sintese, Fala, esperar, tocador: null, gemini: null, orbe: null, config: { provedor: "navegador", vozURI: null, vozGemini: "Kore" } });
    Object.assign(this, { _geracao: 0, _falando: false, _texto: "", _ouvintes: new Set(), _avisos: new Set(), _falhas: 0, _geminiAte: 0, _pre: null, _destravada: false });
  }

  usarGemini(gemini, tocador) { this.gemini = gemini; this.tocador = tocador; }
  usarOrbe(o) { this.orbe = o; }
  configurar(parcial) { Object.assign(this.config, parcial); }
  get falando() { return this._falando; }
  get textoAtual() { return this._texto; }
  disponivel() { return Boolean(this.sintese && this.Fala); }
  aoMudar(fn) { this._ouvintes.add(fn); return () => this._ouvintes.delete(fn); }
  aoAviso(fn) { this._avisos.add(fn); return () => this._avisos.delete(fn); }

  // O iPhone só libera a fala/áudio depois de um toque: chame no primeiro toque (idempotente para a fala; o áudio é retomado a cada vez).
  destravar() {
    this.tocador?.destravar();
    if (this._destravada || !this.disponivel()) return;
    this._destravada = true;
    try { const mudo = new this.Fala(" "); mudo.volume = 0; this.sintese.speak(mudo); } catch { /* sem fala */ }
  }

  _definir(sim, texto = "") {
    this._texto = sim ? texto : "";
    if (sim === this._falando) return;
    this._falando = sim;
    for (const fn of [...this._ouvintes]) { try { fn(sim ? "falando" : "pronta"); } catch { /* ouvinte com defeito */ } }
  }
  _avisar(msg) { for (const fn of [...this._avisos]) { try { fn(msg); } catch { /* idem */ } } }
  _cortar() { try { this.sintese?.cancel(); } catch { /* nada falando */ } this.tocador?.parar(); }
  parar() { this._geracao++; this._pre = null; this._cortar(); this._definir(false); }

  // Termina quando a fala acaba (ou é cortada). Nunca lança: a conversa não pode travar por causa da voz.
  async falar(texto) {
    const partes = prepararPartes(texto);
    if (!partes.length) return;
    this._cortar();
    const minha = ++this._geracao;
    this._pre = null;
    this._definir(true, partes.join(" "));
    try {
      for (let i = 0; i < partes.length && minha === this._geracao; i++) await this._parte(partes[i], partes[i + 1], minha);
    } catch { /* a voz nunca derruba o app */ } finally { if (minha === this._geracao) this._definir(false); }
  }

  _usaGemini() { return this.config.provedor === "gemini" && this.gemini && this.tocador?.disponivel() && Date.now() >= this._geminiAte; }

  async _parte(parte, proxima, minha) {
    if (this._usaGemini()) {
      try {
        const voz = this.config.vozGemini, pronto = this._pre?.parte === parte ? await this._pre.p : await this.gemini.sintetizar(parte, { voz });
        this._pre = null;
        if (minha !== this._geracao) return;
        if (proxima) {  // pede a próxima enquanto esta toca
          const p = this.gemini.sintetizar(proxima, { voz });
          p.catch(() => {});
          this._pre = { parte: proxima, p };
        }
        const visual = this.orbe ? ligarFala(this.orbe, parte, criarPlano(parte, 1).total / ((pronto.pcm.length / pronto.taxa) * 1000 || 1)) : null;
        visual?.inicio();
        try { await this.tocador.tocar(pronto); } finally { visual?.fim(); }
        this._falhas = 0;
        if (minha === this._geracao) await this.esperar(pausaMs(parte));
        return;
      } catch (e) {
        this._pre = null;
        if (minha !== this._geracao) return;
        if (++this._falhas === 1) this._avisar(`Voz do Gemini indisponível (${e.message}): usei a voz do aparelho.`);
        if (this._falhas >= 3) this._geminiAte = Date.now() + 5 * 60 * 1000;  // 3 falhas seguidas: descansa 5 min na voz do aparelho
      }
    }
    await this._navegador(parte, minha);
  }

  _navegador(parte, minha) {
    if (!this.disponivel() || minha !== this._geracao) return Promise.resolve();
    return new Promise((resolver) => {
      const fala = new this.Fala(parte);
      fala.lang = "pt-BR";
      const voz = escolherVoz(this.sintese.getVoices?.() || [], this.config.vozURI);
      if (voz) fala.voice = voz;
      const visual = this.orbe ? ligarFala(this.orbe, parte, fala.rate) : null;  // anima pelo ritmo do texto, não pelo som real
      let feito = false, prazo = null;
      const terminar = () => { if (feito) return; feito = true; clearTimeout(prazo); visual?.fim(); resolver(); };
      fala.onstart = () => visual?.inicio();
      fala.onboundary = (ev) => visual?.limite(ev);
      fala.onend = fala.onerror = terminar;
      prazo = setTimeout(terminar, Math.max(8000, parte.length * 130));  // nunca trava se o navegador não avisar o fim
      try { this.sintese.speak(fala); } catch { terminar(); }
    });
  }

  testar() { return this.falar("Olá, eu sou a Jarvis. Esta é a minha voz. Está boa para você?"); }
}

export const saida = new Saida();

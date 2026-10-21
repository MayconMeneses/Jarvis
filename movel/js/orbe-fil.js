// Orbe de FILAMENTOS do celular (mesma experiência do HUD do PC): Canvas 2D, estados EM ESPERA / OUVINDO / PROCESSANDO / FALANDO,
// 30 fps (15 parado), pausa com a aba oculta ou fora da tela, adapta pelo custo de quadro e respeita os modos de efeitos
// (completo, suave, desligado; "auto" segue "reduzir movimento"). Tem a MESMA interface do Orbe antigo (definirEstado, pulso, fonte,
// estadoAtual, definirModo), então chat.js e orbe-voz.js continuam alimentando o orbe com o envelope sintético da fala.
import { anel, moldura } from "./orbe-filamentos.js";
import { ESTADOS, MODOS, nivelOuvindo } from "./orbe.js";

export const ROTULOS = { ocioso: "EM ESPERA", ouvindo: "OUVINDO", pensando: "PROCESSANDO", falando: "FALANDO" };
// Alvo de cada estado (mesma tabela do PC): cor, brilho, giro (rad/s), velocidade da ondulação, amplitude, espalhamento, radar, spinner.
export const ALVO_BASE = {
  ocioso: { r: 63, g: 208, b: 255, a: 0.6, giro: 0.06, vel: 0.35, amp: 0.3, espalha: 0.14, radar: 0, spin: 0 },
  ouvindo: { r: 63, g: 208, b: 255, a: 0.9, giro: 0.12, vel: 0.8, amp: 1, espalha: 0.1, radar: 1, spin: 0 },
  pensando: { r: 255, g: 154, b: 60, a: 0.85, giro: 0.6, vel: 1.6, amp: 0.35, espalha: 0.06, radar: 0, spin: 1 },
  falando: { r: 110, g: 220, b: 255, a: 0.85, giro: 0.14, vel: 1, amp: 1, espalha: 0.12, radar: 0, spin: 0 },
};
const CAMPOS = ["r", "g", "b", "a", "giro", "vel", "amp", "espalha", "radar", "spin"];
const PERFIL = { completo: { N: 26, M: 80, P: 60, full: true }, suave: { N: 20, M: 48, P: 30, full: false }, leve: { N: 20, M: 56, P: 30, full: true } };

export const perfilDe = (modo, leve) => (modo === "suave" ? PERFIL.suave : leve ? PERFIL.leve : PERFIL.completo);
export function fpsDe(modo, parado, lento) {
  const fps = modo === "suave" ? (parado ? 8 : 20) : parado ? 15 : 30;
  return lento ? Math.min(fps, 20) : fps;
}
// Custo médio por quadro (ms): > 9 corta pela metade os fios; > 12 limita a 20 fps.
export function adaptar(medio, { leve, lento }) {
  if (medio > 9 && !leve) return { leve: true, lento };
  if (medio > 12) return { leve, lento: true };
  return { leve, lento };
}

// Cor CSS (#rgb, #rrggbb ou rgb()) -> [r, g, b], ou null.
export function rgbDe(texto) {
  const t = String(texto || "").trim();
  let m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(t);
  if (m) { const h = m[1].length === 3 ? [...m[1]].map((c) => c + c).join("") : m[1]; return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); }
  m = /^rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/i.exec(t);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

// Alvos já pintados com as cores do tema ativo: espera/ouvindo = acento; processando = laranja; falando = o acento mais claro.
export function alvosDoTema({ ciano, laranja, brilho }) {
  const alvos = Object.fromEntries(Object.entries(ALVO_BASE).map(([k, v]) => [k, { ...v }]));
  const pinta = (e, v) => { if (v) [alvos[e].r, alvos[e].g, alvos[e].b] = v; };
  const c = rgbDe(ciano), gl = rgbDe(brilho) || c;
  pinta("ocioso", c); pinta("ouvindo", c); pinta("pensando", rgbDe(laranja));
  if (c) pinta("falando", c.map((v, i) => Math.round(v + (gl[i] - v) * 0.3)));
  return alvos;
}

export class OrbeFil {
  constructor(canvas, op = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.raf = op.raf || ((f) => requestAnimationFrame(f));
    this.cancelar = op.cancelar || ((id) => cancelAnimationFrame(id));
    this.oculto = op.oculto || (() => document.hidden);
    this.agora = op.agora || (() => performance.now());
    this.cores = op.cores || (() => ({}));
    this.dprMax = op.dprMax || 1.5;
    this.estadoAtual = "ocioso"; this.modo = "completo"; this.fonte = null; this.nivel = 0; this.pulsoVal = 0; this.t = 0;
    this.alvos = alvosDoTema(this.cores());
    this.p = { ...this.alvos.ocioso };
    this.L = 0; this.dpr = 1; this.ph = 0; this.rot = 0; this.giroArco = 0;
    this.leve = false; this.lento = false; this.custo = 0; this.quadros = 0; this.medio = 0;
    this.naTela = true; this._ultimo = 0; this._id = null; this._ativo = false; this._ouvintes = [];
    this._visivel = () => { if (this._ativo) { if (this.oculto()) this._parar(); else this._agendar(); } };
  }

  aoMudar(fn) { this._ouvintes.push(fn); }
  _avisar() { this._ouvintes.forEach((f) => { try { f(this.estadoAtual); } catch { /* tela */ } }); }

  definirEstado(estado) {
    if (!ESTADOS.includes(estado)) return;
    const mudou = estado !== this.estadoAtual;
    this.estadoAtual = estado;
    if (estado !== "falando") this.fonte = null;
    if (this.modo === "desligado") { this._alvoImediato(); this.desenharAgora(); }
    if (mudou) this._avisar();
  }

  definirModo(modo) {
    this.modo = MODOS.includes(modo) ? modo : "completo";
    if (this.modo === "desligado") this._parar(); else if (this._ativo && !this.oculto()) this._agendar();
    this._alvoImediato();
    this.desenharAgora();
  }

  pulso(valor = 0.8) { this.pulsoVal = Math.max(this.pulsoVal, Math.min(1, valor)); }
  recolorir() { this.alvos = alvosDoTema(this.cores()); this._alvoImediato(); this.desenharAgora(); }

  // Largura CSS do canvas (quadrado). O buffer só é refeito quando muda de verdade.
  medir(lado, dpr = 1) {
    lado = Math.max(1, Math.round(lado));
    if (lado === this.L) return false;
    this.L = lado;
    this.dpr = Math.max(1, Math.min(dpr, this.lento ? 1.25 : this.dprMax, 1024 / lado));
    this.canvas.width = this.canvas.height = Math.max(1, Math.round(lado * this.dpr));
    this.desenharAgora();
    return true;
  }

  iniciar() {
    this._ativo = true;
    if (typeof document !== "undefined") document.addEventListener("visibilitychange", this._visivel);
    if (!this.oculto() && this.naTela) this._agendar();
    this.desenharAgora();
  }
  parar() {
    this._ativo = false;
    this._parar();
    if (typeof document !== "undefined") document.removeEventListener("visibilitychange", this._visivel);
  }
  definirNaTela(sim) { this.naTela = Boolean(sim); if (!sim) this._parar(); else if (this._ativo && !this.oculto()) this._agendar(); }

  _agendar() { if (this._id === null && this.modo !== "desligado" && this.naTela) this._id = this.raf((ts) => this._tick(ts)); }
  _parar() { if (this._id !== null) { this.cancelar(this._id); this._id = null; } }
  _tick(ts) {
    this._id = null;
    if (!this._ativo || this.oculto() || !this.naTela || this.modo === "desligado") return;
    this._agendar();
    this.quadro(ts);
  }

  // Um quadro: respeita o limite de fps do estado; devolve true se desenhou.
  quadro(ts) {
    const parado = this.estadoAtual === "ocioso" && this.nivel < 0.02, min = 1000 / fpsDe(this.modo, parado, this.lento);
    if (this._ultimo && ts - this._ultimo < min - 3) return false;
    const dt = this._ultimo ? Math.min(0.1, (ts - this._ultimo) / 1000) : min / 1000;
    this._ultimo = ts;
    const t0 = this.agora();
    this.atualizar(dt, ts);
    this.desenharAgora();
    this.custo += this.agora() - t0;
    if (++this.quadros === 60) {
      this.medio = this.custo / this.quadros;
      Object.assign(this, adaptar(this.medio, this));
      this.custo = 0; this.quadros = 0;
    }
    return true;
  }

  atualizar(dt, ts = 0) {
    const full = perfilDe(this.modo, this.leve).full;
    this.t += dt;
    this.pulsoVal *= Math.exp(-dt / 0.15);
    let base = 0;
    if (this.fonte) base = this.fonte(ts);
    else if (this.estadoAtual === "ouvindo") base = nivelOuvindo(this.t);
    else if (this.estadoAtual === "pensando") base = 0.22 + 0.1 * Math.sin(this.t * 3);
    const alvoN = Math.max(base, this.pulsoVal);
    this.nivel = alvoN + (this.nivel - alvoN) * Math.exp(-dt / (alvoN > this.nivel ? 0.06 : 0.22));  // ataque rápido, queda lenta
    const k = 1 - Math.exp(-dt / 0.25), alvo = this.alvos[this.estadoAtual];
    for (const c of CAMPOS) this.p[c] += (alvo[c] - this.p[c]) * k;  // nunca troca seca de estado
    if (full) { this.ph += this.p.vel * dt; this.rot += this.p.giro * dt; this.giroArco += (0.05 + this.p.spin * 3.2) * dt; }
  }

  _alvoImediato() { this.p = { ...this.alvos[this.estadoAtual] }; }
  desenharAgora() {
    if (!this.L) return;
    const modo = this.modo === "desligado" ? "suave" : this.modo, c = this.modo === "desligado" ? { N: 20, M: 48, P: 0, full: false } : perfilDe(modo, this.leve);
    const g = { C: this.L / 2, R: this.L / 2 }, n = this.modo === "desligado" ? 0 : this.nivel;
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, this.L, this.L);
    ctx.globalCompositeOperation = "lighter";
    anel(ctx, g, this.p, n, this.ph, this.rot, this.giroArco, c);
    moldura(ctx, g, this.p, n, this.giroArco, c.full);
    ctx.globalCompositeOperation = "source-over";
  }

  depurar() {
    return { rodando: this._id !== null, lado: this.L, dpr: this.dpr, filamentos: perfilDe(this.modo, this.leve).N, leve: this.leve, lento: this.lento,
      custoMsPorQuadro: +this.medio.toFixed(2), estado: this.estadoAtual, nivel: this.nivel, modo: this.modo };
  }
}

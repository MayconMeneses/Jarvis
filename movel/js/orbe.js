// Orbe reativo: estados ocioso/ouvindo/pensando/falando, nível 0..1 suavizado, 30 fps (15 parado, 10 no modo suave),
// DPR até 2, pausa com a aba oculta e respeita "reduzir movimento". Modos: completo, suave (só brilho) e desligado (imagem parada).
import { desenhar, PRESETS } from "./orbe-desenho.js";

export const ESTADOS = ["ocioso", "ouvindo", "pensando", "falando"];
export const MODOS = ["completo", "suave", "desligado"];
export const FPS = { ocioso: 15, ouvindo: 30, pensando: 30, falando: 30 };
export const FPS_SUAVE = 10;

// A escolha do usuário manda; sem escolha ("auto"), o sistema decide pelo "reduzir movimento".
export const modoEfetivo = (escolha, reduzir) => (MODOS.includes(escolha) ? escolha : reduzir ? "suave" : "completo");

// Respiração e tremor leve da escuta, quando não há nível real (o reconhecimento de fala não expõe o áudio).
export const nivelOuvindo = (t) => 0.2 + 0.1 * Math.sin(t * 2.1) + 0.06 * Math.sin(t * 5.3 + 1);

export class Orbe {
  constructor(canvas, op = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.raf = op.raf || ((f) => requestAnimationFrame(f));
    this.cancelar = op.cancelar || ((id) => cancelAnimationFrame(id));
    this.oculto = op.oculto || (() => document.hidden);
    this.dprMax = op.dprMax || 2;
    this.dpr = 1; this.largura = canvas.width; this.altura = canvas.height;
    this.estadoAtual = "ocioso"; this.modo = "completo";
    this.nivel = 0; this.pulsoVal = 0; this.t = 0; this.fonte = null;
    this.p = { ...PRESETS.ocioso, cor: [...PRESETS.ocioso.cor] };
    this._ultimo = 0; this._id = null; this._ativo = false;
    this._visivel = () => { if (this._ativo) { if (this.oculto()) this._parar(); else this._agendar(); } };
  }

  redimensionar(largura, altura, dpr = 1) {
    this.dpr = Math.min(this.dprMax, Math.max(1, dpr));
    this.largura = largura; this.altura = altura;
    this.canvas.width = Math.round(largura * this.dpr);
    this.canvas.height = Math.round(altura * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    this.desenharAgora();
  }

  definirEstado(estado) {
    if (!ESTADOS.includes(estado)) return;
    this.estadoAtual = estado;
    if (estado !== "falando") this.fonte = null;
    if (this.modo === "desligado") { this._alvoImediato(); this.desenharAgora(); }
  }

  definirModo(modo) {
    this.modo = MODOS.includes(modo) ? modo : "completo";
    if (this.modo === "desligado") this._parar(); else if (this._ativo && !this.oculto()) this._agendar();
    this._alvoImediato();
    this.desenharAgora();
  }

  pulso(valor = 0.8) { this.pulsoVal = Math.max(this.pulsoVal, Math.min(1, valor)); }

  iniciar() {
    this._ativo = true;
    if (typeof document !== "undefined") document.addEventListener("visibilitychange", this._visivel);
    if (!this.oculto()) this._agendar();
    this.desenharAgora();
  }

  parar() {
    this._ativo = false;
    this._parar();
    if (typeof document !== "undefined") document.removeEventListener("visibilitychange", this._visivel);
  }

  _agendar() { if (this._id === null && this.modo !== "desligado") this._id = this.raf((ts) => this._tick(ts)); }
  _parar() { if (this._id !== null) { this.cancelar(this._id); this._id = null; } }
  _tick(ts) {
    this._id = null;
    if (!this._ativo || this.oculto() || this.modo === "desligado") return;
    this._agendar();
    this.quadro(ts);
  }

  // Um quadro: respeita o limite de fps do estado; devolve true se desenhou.
  quadro(ts) {
    const fps = this.modo === "suave" ? FPS_SUAVE : FPS[this.estadoAtual];
    if (this._ultimo && ts - this._ultimo < 1000 / fps - 2) return false;
    const dt = this._ultimo ? Math.min(0.1, (ts - this._ultimo) / 1000) : 1 / fps;
    this._ultimo = ts;
    this.atualizar(dt, ts);
    this.desenharAgora();
    return true;
  }

  atualizar(dt, ts = 0) {
    this.t += this.modo === "completo" ? dt : dt * 0.25;
    this.pulsoVal *= Math.exp(-dt / 0.15);
    let base = 0;
    if (this.fonte) base = this.fonte(ts);
    else if (this.estadoAtual === "ouvindo") base = nivelOuvindo(this.t);
    else if (this.estadoAtual === "pensando") base = 0.25 + 0.1 * Math.sin(this.t * 3);
    const alvo = Math.max(base, this.pulsoVal);
    this.nivel = alvo + (this.nivel - alvo) * Math.exp(-dt / (alvo > this.nivel ? 0.06 : 0.22));  // ataque rápido, queda lenta
    const k = 1 - Math.exp(-dt / 0.25), preset = PRESETS[this.estadoAtual];  // nunca troca seca de estado
    for (let i = 0; i < 3; i++) this.p.cor[i] += (preset.cor[i] - this.p.cor[i]) * k;
    for (const c of ["alfa", "giro", "spin", "radar"]) this.p[c] += (preset[c] - this.p[c]) * k;
  }

  _alvoImediato() { const pre = PRESETS[this.estadoAtual]; this.p = { ...pre, cor: [...pre.cor] }; }
  desenharAgora() { desenhar(this.ctx, this.largura, this.altura, { ...this.p, nivel: this.nivel, t: this.t, modo: this.modo === "completo" ? "completo" : "suave" }); }
}

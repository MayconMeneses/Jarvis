// Escuta contínua por TEXTO enquanto o app está aberto e em primeiro plano (iPhone/Safari). Nada de áudio é guardado: o reconhecimento é o do
// navegador (no iPhone, a Apple processa a fala) e aqui só passa texto. Ativa se a frase COMEÇA com "Jarvis" ou o chama no FIM ("oi, boa noite, Jarvis"): voz-ativacao.js.
// Estados: desligado, aguardando, ouvindo, processando, falando. API para a casca/modo foco: iniciar(), parar(), estado, aoMudar(fn).
// Reinício robusto: o Safari encerra a sessão sozinho (silêncio/tempo); cada fim abre uma sessão NOVA, com espera crescente, e para de vez
// depois de muitas falhas seguidas ou se o microfone foi negado. Anti-eco: ignora o microfone enquanto a Jarvis fala e ~0,5 s depois.
import { LimitadorAtivacao } from "./limitador-ativacao.js";
import { eEcoDe, extrairChamada as extrairComando } from "./voz-ativacao.js";

export const ESTADOS = ["desligado", "aguardando", "ouvindo", "processando", "falando"];
export const JANELA_COMANDO_MS = 6000;  // "Jarvis" sozinho: o comando pode vir na frase seguinte, até este prazo
export const CAUDA_ECO_MS = 500;        // depois que a Jarvis termina de falar o microfone ainda fica surdo por este tempo
export const SESSAO_BOA_MS = 1500;      // sessão que durou menos que isto, sem resultado, conta como falha
export const MAX_FALHAS = 8;
const ESPERAS = [150, 300, 600, 1200, 2500, 4000];

export class EscutaContinua {
  constructor({ Reconhecimento = globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition, agora = () => Date.now(), esperar = (f, ms) => setTimeout(f, ms),
    cancelar = (t) => clearTimeout(t), idioma = "pt-BR", seguro = globalThis.isSecureContext !== false } = {}) {
    Object.assign(this, { Reconhecimento, agora, esperar, cancelar, idioma, seguro, _limite: new LimitadorAtivacao({ agora }) });
    Object.assign(this, { _estado: "desligado", _quer: false, _suspensos: 0, _oculta: false, _rec: null, _falhas: 0, _inicio: 0, _recebeu: false, _sessaoRuim: false,
      _tReinicio: null, _tJanela: null, _janela: false, _falando: false, _bloqueadoAte: 0, _ouvintes: new Set(), _processando: false, _fila: null,
      _motivo: null, _antesFoco: null, _cfg: { focoAuto: true } });
  }

  // Ligações com o resto do app (todas opcionais): aoComando(texto) async, interromper() corta a fala, textoFalado() = o que ela diz agora, aoIniciar().
  configurar(parcial) { Object.assign(this._cfg, parcial); return this; }
  disponivel() { return Boolean(this.Reconhecimento) && this.seguro; }
  get estado() { return this._estado; }
  get ativa() { return this._quer; }
  get motivo() { return this._motivo; }
  aoMudar(fn) { this._ouvintes.add(fn); return () => this._ouvintes.delete(fn); }

  iniciar() {
    if (!this.disponivel()) { this._motivo = "sem-suporte"; this._avisar("sem-suporte"); return false; }
    this._quer = true; this._motivo = null; this._falhas = 0;
    try { this._cfg.aoIniciar?.(); } catch { /* destravar o áudio é só um reforço */ }
    this._abrir();
    this._definir(this._base(), { evento: "ligada" });
    return true;
  }

  parar(motivo = null) {
    this._quer = false; this._janela = false; this._fila = null; this._motivo = motivo;
    this.cancelar(this._tReinicio); this.cancelar(this._tJanela);
    this._fechar();
    this._definir("desligado", { evento: "parou", motivo });
  }

  // Tocou em "Falar" (foco): a PRIMEIRA frase vale como comando mesmo sem o nome, por `ms`. Depois volta a exigir "Jarvis".
  escutarAgora(ms = 10000) { if (this._quer) this._abrirJanela(ms); }

  // Modo foco: liga ao entrar (se voz_foco_auto) e devolve ao estado anterior ao sair.
  entrarFoco() {
    if (this._antesFoco === null) this._antesFoco = this._quer;
    return this._cfg.focoAuto === false ? false : (this._quer || this.iniciar());
  }
  sairFoco() {
    const antes = this._antesFoco;
    this._antesFoco = null;
    if (antes === false && this._quer) this.parar();
  }

  // Outro recurso (ditado, conversa por voz) precisa do microfone: solta o nosso e devolve quem religa. O iOS só tem UM reconhecimento por vez.
  async suspender() {
    this._suspensos++;
    if (this._suspensos === 1) { this.cancelar(this._tReinicio); this._fechar(); if (this._quer) await new Promise((r) => this.esperar(r, 250)); }
    let feito = false;
    return () => {
      if (feito) return;
      feito = true;
      if (--this._suspensos === 0 && this._quer) { this._falhas = 0; this._tReinicio = this.esperar(() => this._abrir(), 400); }
    };
  }

  // Aba oculta/tela bloqueada: o iOS corta o microfone de qualquer jeito; fechamos de propósito e religamos ao voltar.
  visibilidade(visivel) {
    this._oculta = !visivel;
    if (!visivel) { this.cancelar(this._tReinicio); this._fechar(); } else if (this._quer && !this._suspensos) { this._falhas = 0; this._abrir(); }
  }

  // A saída (voz) avisa quando começa e quando termina de falar: anti-eco.
  marcarFala(sim) {
    if (sim) { this._falando = true; this._fecharJanela(); } else {
      this._falando = false; this._bloqueadoAte = this.agora() + CAUDA_ECO_MS;
      if (this._quer && !this._suspensos) { this._fechar(); this._tReinicio = this.esperar(() => this._abrir(), CAUDA_ECO_MS); }  // descarta o que o eco deixou pendente
    }
    if (this._quer) this._definir(this._base());
  }

  // ── sessão do reconhecimento ──────────────────────────────────────────
  _abrir() {
    if (this._rec || !this._quer || this._suspensos || this._oculta || !this.disponivel()) return;
    let rec;
    try {
      rec = new this.Reconhecimento();
      Object.assign(rec, { lang: this.idioma, continuous: true, interimResults: true, maxAlternatives: 1 });
      rec.onstart = () => { if (rec === this._rec) this._inicio = this.agora(); };
      rec.onresult = (ev) => { if (rec === this._rec) this._resultado(ev); };
      rec.onerror = (ev) => { if (rec === this._rec) this._erro(ev?.error); };
      rec.onend = () => { if (rec === this._rec) this._fim(); };
      this._rec = rec; this._inicio = this.agora(); this._recebeu = false; this._sessaoRuim = false;
      rec.start();
    } catch { this._rec = null; this._falhou(); }
  }

  _fechar() {
    const rec = this._rec;
    this._rec = null;
    if (!rec) return;
    rec.onstart = rec.onresult = rec.onerror = rec.onend = null;  // a sessão velha não fala mais com a gente
    try { rec.abort(); } catch { /* já tinha terminado */ }
  }

  _fim() {
    const durou = this.agora() - this._inicio;
    this._rec = null;
    if (!this._quer || this._suspensos || this._oculta) return;
    if (this._recebeu || (durou >= SESSAO_BOA_MS && !this._sessaoRuim)) this._falhas = 0; else this._falhas++;
    this._reabrir();
  }

  _falhou() { this._falhas++; if (this._quer) this._reabrir(); }

  _reabrir() {
    if (this._falhas >= MAX_FALHAS) { this.parar("instavel"); return; }
    this.cancelar(this._tReinicio);
    this._tReinicio = this.esperar(() => this._abrir(), this._falhas ? ESPERAS[Math.min(this._falhas - 1, ESPERAS.length - 1)] : 100);
  }

  _erro(codigo) {
    if (codigo === "not-allowed" || codigo === "service-not-allowed") this.parar("permissao");
    else if (codigo === "audio-capture") this.parar("microfone");
    else if (codigo === "language-not-supported") this.parar("idioma");
    else if (codigo !== "no-speech" && codigo !== "aborted") this._sessaoRuim = true;  // network e outros: o fim da sessão conta como falha
  }

  // ── o que foi ouvido ───────────────────────────────────────────────────
  _bloqueada() { return this._falando || this.agora() < this._bloqueadoAte; }

  _resultado(ev) {
    this._recebeu = true; this._falhas = 0;
    for (let i = ev.resultIndex || 0; i < (ev.results?.length || 0); i++) {
      const r = ev.results[i], texto = String(r?.[0]?.transcript || "").trim();
      if (!texto) continue;
      if (this._bloqueada() && !this._furarEco(r.isFinal, texto)) continue;  // era o eco da própria fala (ou a cauda dele)
      if (!r.isFinal) { if (!this._janela && this._estado === "aguardando" && extrairComando(texto) !== null) this._definir("ouvindo", { evento: "chamada" }); continue; }
      this._tratar(texto);
    }
  }

  // Barge-in: ouviu "Jarvis" no começo e NÃO é a própria fala dela voltando pelo microfone: corta a fala e passa a ouvir.
  _furarEco(final, texto) {
    if (!this._falando || final || extrairComando(texto) === null) return false;
    if (eEcoDe(texto, this._cfg.textoFalado?.() || "")) return false;
    try { this._cfg.interromper?.(); } catch { /* sem fala para cortar */ }
    this._falando = false; this._bloqueadoAte = 0;
    return true;
  }

  _tratar(texto) {
    let comando = extrairComando(texto);
    const nomeado = comando !== null;
    if (this._janela) {  // "Jarvis" veio sozinho antes: a frase seguinte é o comando, com ou sem o nome
      this._fecharJanela();
      if (comando === null) comando = texto;
      else if (comando === "") { this._abrirJanela(); return; }
    }
    if (comando === null) { if (this._estado === "ouvindo") this._definir(this._base()); return; }  // não era com ela
    if (nomeado && !this._limite.permite()) { this._definir(this._base()); return; }  // rajada de ativações (áudio de fundo): ignora
    if (comando === "") this._abrirJanela(); else this._despachar(comando);
  }

  _abrirJanela(ms = JANELA_COMANDO_MS) {
    this._janela = true;
    this.cancelar(this._tJanela);
    this._tJanela = this.esperar(() => { this._fecharJanela(); if (this._quer) this._definir(this._base()); }, ms);
    this._definir("ouvindo", { evento: "chamada" });
  }

  _fecharJanela() { this._janela = false; this.cancelar(this._tJanela); }

  _despachar(comando) {
    if (this._processando) { this._fila = comando; return; }  // um pedido por vez; só o mais recente espera
    this._processando = true;
    this._definir("processando", { evento: "comando", texto: comando });
    Promise.resolve().then(() => this._cfg.aoComando?.(comando)).catch(() => {}).finally(() => {
      this._processando = false;
      const proximo = this._fila;
      this._fila = null;
      if (this._quer && proximo) this._despachar(proximo); else if (this._quer) this._definir(this._base());
    });
  }

  _base() {
    if (!this._quer) return "desligado";
    if (this._falando) return "falando";
    if (this._processando) return "processando";
    return this._janela ? "ouvindo" : "aguardando";
  }

  _definir(estado, info = {}) {
    if (estado === this._estado && !info.evento) return;
    this._estado = estado;
    for (const fn of [...this._ouvintes]) { try { fn(estado, { motivo: this._motivo, ...info }); } catch { /* ouvinte com defeito não derruba a escuta */ } }
  }

  _avisar(evento) { for (const fn of [...this._ouvintes]) { try { fn(this._estado, { evento, motivo: this._motivo }); } catch { /* idem */ } } }
}

export const Escuta = new EscutaContinua();

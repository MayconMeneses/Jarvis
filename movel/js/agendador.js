// Dispara uma tarefa quando o app está aberto e SEM uso há um tempo (10 min). Depois de cada disparo exige outro intervalo ocioso,
// então o trabalho se espalha. Relógio e temporizador são injetáveis para teste. Não funciona com o app fechado (limite do iPhone).
export const OCIOSO_MS = 10 * 60 * 1000, PASSO_MS = 60 * 1000;

export class Agendador {
  constructor({ tarefa, relogio = () => Date.now(), ociosoMs = OCIOSO_MS, passoMs = PASSO_MS, ligarTimer = (fn, ms) => setInterval(fn, ms), pararTimer = (t) => clearInterval(t), aoBater = null }) {
    Object.assign(this, { aoBater, tarefa, relogio, ociosoMs, passoMs, ligarTimer, pararTimer });
    this.ultima = relogio(); this.timer = null; this.rodando = false;
  }

  bater(estado) { try { this.aoBater?.(estado); } catch { /* o batimento é opcional */ } }  // prova de vida para o painel de Agentes
  atividade() { this.ultima = this.relogio(); }
  iniciar() { if (!this.timer) this.timer = this.ligarTimer(() => this.passo(), this.passoMs); }
  parar() { if (this.timer) this.pararTimer(this.timer); this.timer = null; }

  async passo() {
    if (this.rodando) return false;
    if (this.relogio() - this.ultima < this.ociosoMs) { this.bater("ocioso"); return false; }
    this.rodando = true;
    let estado = "ok";
    try { await this.tarefa(); } catch (e) { estado = "erro"; /* a tarefa trata os próprios erros; aqui só não pode derrubar o app */ } finally {
      this.bater(estado); this.rodando = false; this.ultima = this.relogio(); }
    return true;
  }
}

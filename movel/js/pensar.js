// "Como pensar": decide QUEM responde quando as regras do motor não bastam, e garante que TODO pedido termina com UMA resposta ou um erro claro.
//   automatico (padrão): cérebro do aparelho (se ligado e saudável) -> nuvem (se houver chave) -> só regras. Desligou o cérebro? A nuvem assume sozinha.
//   aprender: só aparelho e regras, NUNCA nuvem (nem a Oficina, nem documentos): a Jarvis registra o que não entendeu e evolui sem enviar nada para fora.
//   nuvem: só a nuvem, com erro claro se não houver chave.
// Lógica pura (dependências injetadas): testável no Node.
import { limite } from "./limite.js";

export const MODOS = ["automatico", "aprender", "nuvem"];
export const ROTULOS = { automatico: "Automático (recomendado)", aprender: "Aprender (só no aparelho, sem nuvem)", nuvem: "Só nuvem" };
export const NOTAS = {
  automatico: "Usa o cérebro do aparelho se estiver ligado; se estiver desligado, lento ou falhar, passa sozinha para a nuvem (se houver chave) e, por fim, para as regras.",
  aprender: "Nada sai do aparelho: não uso a nuvem. Registro o que não entendi para aprender com você (veja \"o que você aprendeu\"). Bom para a Jarvis evoluir sozinha.",
  nuvem: "Usa só a nuvem (precisa de chave cadastrada abaixo). Mais capaz, mas envia a conversa ao provedor que você escolheu.",
};
export const LIMITE_MS = 25000;                   // cada tentativa de IA; passou disso, desiste e segue para o próximo caminho
export const PAUSA_APARELHO_MS = 10 * 60 * 1000;  // 2 falhas seguidas do cérebro do aparelho: descansa 10 min se houver nuvem
export const AVISO_NUVEM = "Cérebro do aparelho desligado: usando a nuvem.";
export const SEM_CHAVE_NUVEM = "Estou no modo \"Só nuvem\", mas não há chave de nuvem cadastrada. Toque em Cérebro > Nuvem e cadastre uma chave, ou mude \"Como pensar\" para Automático.";
export const NOTA_APRENDER = "Estou no modo aprender: só uso o aparelho e as regras, sem nuvem. Guardei esta frase para aprender com você; se quiser, me ensine: \"isso significa ...\".";
export const DICA_SEM_CEREBRO = "Dica: o cérebro do aparelho está desligado e não há chave de nuvem, então respondo só com as regras. Para respostas livres, toque em Cérebro e ligue um dos dois.";

export class Pensador {
  // d: { motor, cerebro, nuvem, memoria, caminhos: { perguntarAparelho, perguntarNuvem }, mostrar(texto, widget, classe), erro(texto), avisar(texto), limiteMs, agora }
  constructor(d) {
    Object.assign(this, { limiteMs: LIMITE_MS, agora: () => Date.now() }, d);
    Object.assign(this, { modoAtual: "automatico", _ouvintes: new Set(), _usou: null, _avisouNuvem: false, _dicaDada: false, _falhasAparelho: 0, _pausaAte: 0 });
  }

  async iniciar() { const m = await this.memoria.meta("cerebro_modo"); this.modoAtual = MODOS.includes(m) ? m : "automatico"; await this._emitir(); return this; }
  async definirModo(modo) {
    if (!MODOS.includes(modo)) return;
    this.modoAtual = modo; this._usou = null;
    await this.memoria.definirMeta("cerebro_modo", modo);
    await this._emitir();
  }

  aoMudar(fn) { this._ouvintes.add(fn); return () => this._ouvintes.delete(fn); }
  async _emitir() { const t = await this.status(); for (const f of [...this._ouvintes]) { try { f(t, this.modoAtual); } catch { /* tela */ } } }

  // Rótulo curto de quem vai responder agora (aparece no foco e na conversa).
  async status() {
    const m = this.modoAtual, nuvem = await this.nuvem.configurada();
    if (m === "aprender") return "cérebro: aprender (só aparelho)";
    if (m === "nuvem") return nuvem ? "cérebro: nuvem" : "cérebro: nuvem (sem chave)";
    return `cérebro: ${this.cerebro.ligado() ? "aparelho" : nuvem ? "nuvem" : "regras"} (automático)`;
  }

  // Chamado quando o cérebro do aparelho liga ou desliga (painel Cérebro).
  async cerebroMudou(ligado) {
    if (ligado) { this._avisouNuvem = false; this._falhasAparelho = 0; this._pausaAte = 0; }
    else if (this.modoAtual === "automatico" && await this.nuvem.configurada() && !this._avisouNuvem) { this._avisouNuvem = true; this.avisar(AVISO_NUVEM); }
    await this._emitir();
  }

  async plano() {
    const m = this.modoAtual, nuvem = await this.nuvem.configurada(), tentativas = [];
    if (m === "aprender") return { tentativas };
    if (m === "nuvem") return nuvem ? { tentativas: [["nuvem", this.caminhos.perguntarNuvem]] } : { tentativas, erro: SEM_CHAVE_NUVEM };
    const aparelho = this.cerebro.ligado() && !(nuvem && this.agora() < this._pausaAte);
    if (aparelho) tentativas.push(["aparelho", this.caminhos.perguntarAparelho]);
    if (nuvem) tentativas[(await this.memoria.meta("nuvem_ordem")) === "nuvem" ? "unshift" : "push"](["nuvem", this.caminhos.perguntarNuvem]);
    if (nuvem && !this.cerebro.ligado() && !this._avisouNuvem) { this._avisouNuvem = true; this.avisar(AVISO_NUVEM); }
    return { tentativas };
  }

  // Um pedido qualquer. SEMPRE devolve um texto não vazio (já mostrado) e nunca lança.
  async pensar(texto) {
    const total = this.limiteMs * 2 + 5000;
    try {
      return await limite(this._pensar(texto), total, `demorei mais de ${Math.round(total / 1000)} s para responder. Tente de novo; se repetir, troque o cérebro em Cérebro > Como pensar`);
    } catch (e) {
      const msg = `Não consegui responder: ${e.message}. A conversa continua: pode perguntar de novo.`;
      this.erro(msg);
      return msg;
    }
  }

  async _pensar(texto) {
    const { motor } = this;
    motor.entendimento?.tomarWidget();
    const regras = await motor.responder(texto);  // regras e entendimento (sem IA) primeiro: dados exatos, instantâneo, sem gastar bateria
    if (typeof regras === "string" && regras.trim()) { this._usou = "regras"; this.mostrar(regras, motor.entendimento?.tomarWidget()); return regras; }
    const plano = await this.plano();
    if (plano.erro) { this.erro(plano.erro); return plano.erro; }
    if (plano.tentativas.length) {
      await motor.entendimento?.registrarIA(texto);
      for (const [via, tentar] of plano.tentativas) {
        try {
          const r = await tentar(texto, this.limiteMs);
          if (via === "aparelho") this._falhasAparelho = 0;
          this._usou = via; await this._emitir();
          return r;
        } catch (e) {
          if (via === "aparelho" && ++this._falhasAparelho >= 2) this._pausaAte = this.agora() + PAUSA_APARELHO_MS;
          this.mostrar(`Não consegui pelo ${via === "aparelho" ? "cérebro do aparelho" : "cérebro da nuvem"} (${e.message}).`, null, "jarvis aviso");
        }
      }
    }
    return this._soRegras(texto, plano.tentativas.length > 0);
  }

  async _soRegras(texto, falhou) {
    this._usou = "regras";
    let resposta = await this.motor.fallback(texto);
    if (!String(resposta || "").trim()) resposta = "Não entendi esse pedido. Pode dizer de outro jeito?";
    const widget = this.motor.entendimento?.tomarWidget();
    if (falhou) resposta += "\n\nA IA não respondeu agora; respondi só com as regras. Pode tentar de novo.";
    else if (this.modoAtual === "aprender") resposta += "\n\n" + NOTA_APRENDER;
    else if (!this._dicaDada) { this._dicaDada = true; resposta += "\n\n" + DICA_SEM_CEREBRO; }
    this.mostrar(resposta, widget);
    await this._emitir();
    return resposta;
  }
}

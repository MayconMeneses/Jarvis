// Atualização leve do painel "PC": só roda com a aba do PC aberta, a página visível e o PC pareado. Nunca em segundo plano.
export class Atualizador {
  constructor({ atualizar, visivel, ativo, pareado, intervaloMs = 30000, agendar = (f, ms) => setInterval(f, ms), cancelar = (id) => clearInterval(id) }) {
    Object.assign(this, { atualizar, visivel, ativo, pareado, intervaloMs, agendar, cancelar });
    this.id = null;
    this.rodando = false;
  }

  async tick() {
    if (this.rodando || !this.visivel() || !this.ativo() || !(await this.pareado())) return false;
    this.rodando = true;  // sem sobreposição: se o PC está lento, o próximo ciclo espera
    try { await this.atualizar(); } catch { /* o cartão já mostra o aviso */ } finally { this.rodando = false; }
    return true;
  }

  iniciar() { if (this.id === null) this.id = this.agendar(() => this.tick(), this.intervaloMs); }
  parar() { if (this.id !== null) { this.cancelar(this.id); this.id = null; } }
}

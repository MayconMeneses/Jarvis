// No máximo `n` ativações pelo nome por `janelaMs`: uma TV ou um vídeo de fundo citando "Jarvis" não vira uma rajada de comandos.
// Porte de LimitadorAtivacao (jarvis/voice/chamada.py). Lógica pura, com relógio injetável.
export class LimitadorAtivacao {
  constructor({ n = 5, janelaMs = 60000, agora = () => Date.now() } = {}) { Object.assign(this, { n, janelaMs, agora, _marcas: [] }); }
  permite() {
    const t = this.agora();
    while (this._marcas.length && t - this._marcas[0] > this.janelaMs) this._marcas.shift();
    if (this._marcas.length >= this.n) return false;
    this._marcas.push(t);
    return true;
  }
}

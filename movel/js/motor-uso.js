// Pedido de conversa "quanto gastei" / "uso de IA". O objeto `uso` é ligado pelo main.js depois de criar o motor.
const EXTRAS = [["uso_ia", /^(quanto (eu )?gastei( (com|de) (ia|nuvem|tokens))?( (este|esse|neste|nesse) mes)?|uso de ia|gasto com ia|meu uso de ia|quantos tokens (eu )?(usei|gastei))$/]];
const HANDLERS = { _uso_ia() { return this.uso ? this.uso.relatorio() : "O painel de uso de IA ainda não está carregado."; } };

export function instalarUso(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}

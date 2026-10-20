// Pedidos de conversa da Jarvis autônoma: "o que você aprendeu" e "avaliar cérebro". Os objetos (autonomo, avaliador) são ligados
// pelo main.js depois de criar o motor; sem eles, o motor explica o que falta em vez de falhar.
const EXTRAS = [
  ["aprendeu", /^(o que (voce )?(ja )?(aprendeu|estudou)( sozinha)?( ate agora| recentemente)?|(quais|que) (sao )?(os )?assuntos (voce )?(aprendeu|estudou).*)$/],
  ["avaliar_cerebro", /^(avali\w+ (o |meu |seu )*cerebro( agora)?|como esta (o |meu |seu )*cerebro|testar? (o |meu |seu )*cerebro|nota do (meu |seu )*cerebro)$/],
];

const HANDLERS = {
  _aprendeu() { return this.autonomo ? this.autonomo.relatorio() : "A parte de aprender sozinha ainda não está carregada."; },
  async _avaliar_cerebro(texto, limpo) {
    if (!this.avaliador) return "A avaliação do cérebro ainda não está carregada.";
    return /^como esta|^nota do/.test(limpo) ? this.avaliador.resumo() : this.avaliador.executar();
  },
};

export function instalarAutonomo(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}

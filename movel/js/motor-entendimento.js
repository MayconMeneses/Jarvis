// Pedidos do motor sobre o próprio entendimento: ajuda curta e contextual, "como estou evoluindo" e apagar o que ela aprendeu sobre como você fala.
const EXTRAS = [
  ["evolucao_fala", /^(o que (voce )?(ja )?aprendeu (sobre|com|de) (como eu falo|minha fala|o meu jeito de falar|meu jeito de falar|minhas frases|mim e das minhas frases)|como (voce )?(esta|estou) evoluindo|relatorio de evolucao|voce esta (me )?entendendo melhor|taxa de entendimento)$/],
  ["esquecer_fala", /^(apag\w+|esquec\w+|limp\w+|zer\w+)\s+(tudo\s+)?(o\s+)?(que\s+)?(voce\s+)?(aprendeu|aprendizado|atalhos)(\s+(sobre|de|com)\s+(como eu falo|minha fala|mim))?$/],
  ["ensinar", /^(ei |ok )?quando eu (disser|falar|digitar|escrever|pedir|mandar)\b.+$/],
];

const HANDLERS = {
  // Ajuda CURTA e do momento: 4 sugestões escolhidas pelo que o app ainda não tem configurado. Nunca a lista inteira de funções.
  async _ajuda() {
    const e = this.entendimento, estado = e ? await e.estado() : {};
    const dicas = [];
    if (!estado.ultimaCopia) dicas.push('"como faço cópia de segurança" (você ainda não fez uma)');
    if (estado.nuvem === false) dicas.push('"onde coloco a chave do Gemini" (para eu usar uma IA maior)');
    if (estado.pc === false) dicas.push('"como parear com o PC"');
    dicas.push('"como colocar a Jarvis em outro celular"', '"notícias de tecnologia"', '"o que é o modo foco"', '"o que você aprendeu sobre como eu falo"');
    return "Eu entendo o dia a dia sem precisar de IA e também explico o próprio app. Experimente:\n" + dicas.slice(0, 4).map((d) => `- ${d}`).join("\n")
      + '\n\nSe eu não entender, eu digo, mostro o mais perto e você pode me ensinar: "quando eu disser X, mostre minha agenda".';
  },

  async _evolucao_fala() {
    if (!this.entendimento) return "Ainda não estou medindo o entendimento neste aparelho.";
    this.entendimento.widget = { tipo: "botoes", botoes: [{ rotulo: "Apagar tudo que aprendi", apagarAprendizado: true }] };
    return this.entendimento.aprend.relatorio();
  },

  async _esquecer_fala() {
    if (this.entendimento) await this.entendimento.aprend.apagarTudo();
    return "Apaguei tudo que aprendi sobre como você fala (frases não entendidas, escolhas, atalhos e contagens). Começo do zero.";
  },

  _ensinar() { return 'Diga assim: "quando eu disser bom dia chefe, mostre minha agenda". Eu mostro um cartão e só guardo se você tocar em Guardar.'; },
};

export function instalarEntendimento(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}

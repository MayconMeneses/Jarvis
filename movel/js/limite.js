// Prazo para qualquer espera que possa travar (IA, nuvem, fala): depois dele a promessa REJEITA com uma mensagem clara, em vez de deixar o app em "pensando" para sempre.
export function limite(promessa, ms, mensagem) {
  let relogio;
  const prazo = new Promise((_, rejeitar) => { relogio = setTimeout(() => rejeitar(new Error(mensagem || `demorou mais de ${Math.round(ms / 1000)} s`)), ms); });
  return Promise.race([Promise.resolve(promessa), prazo]).finally(() => clearTimeout(relogio));
}

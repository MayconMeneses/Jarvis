// Mensagens de erro em português claro: o que houve e o que a pessoa pode fazer. Nunca mostra o código técnico sozinho.
const CASOS = [
  [/service-not-allowed/i, "A fala por voz está desligada no iPhone. Ative o Ditado em Ajustes → Geral → Teclado."],
  [/not-allowed|permission|denied|NotAllowedError/i, "O Safari não liberou o microfone. Permita nas configurações do site (aA na barra do Safari) e tente de novo."],
  [/no-speech|aborted/i, "Não ouvi nada. Fale mais perto do microfone."],
  [/audio-capture|NotFoundError/i, "Não encontrei um microfone neste aparelho."],
  [/quota|QuotaExceeded|full/i, "O aparelho está sem espaço para guardar isso. Apague notas antigas ou libere espaço do iPhone e tente de novo."],
  [/InvalidStateError|SecurityError|private|indexeddb/i, "Este navegador não deixa guardar dados (modo privado?). O que você fizer vale só enquanto o app estiver aberto."],
  [/webgpu/i, "Este aparelho não tem WebGPU. O motor de regras continua respondendo normalmente."],
  [/Failed to fetch|NetworkError|Load failed|network/i, "Não consegui falar com a internet. Confira a conexão e tente de novo."],
];

export function erroHumano(e, padrao = "Algo deu errado.") {
  const bruto = String(e?.name && e?.message ? `${e.name} ${e.message}` : e?.message || e || "");
  const legivel = String(e?.message || e || "");
  for (const [regra, texto] of CASOS) if (regra.test(bruto)) return texto;
  const limpo = legivel.replace(/\s+/g, " ").trim().slice(0, 160);
  return limpo ? `${padrao} (${limpo})` : padrao;
}

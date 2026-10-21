// Escolha da MELHOR voz pt-BR do aparelho. No iPhone as vozes boas (Luciana, Felipe, "Aprimorada"/"Premium") só existem se o usuário as baixou
// (Ajustes > Acessibilidade > Conteúdo falado > Vozes > Português (Brasil)). Esta função só ordena o que o navegador devolve em getVoices().
const NOVIDADE = /\b(eddy|flo|grandma|grandpa|reed|rocko|sandy|shelley|bad news|bells|boing|bubbles|cellos|good news|jester|organ|superstar|trinoids|whisper|zarvox|albert|fred|junior|kathy|ralph)\b/i;

export const normalizarLang = (v) => String(v?.lang || "").replace("_", "-").toLowerCase();
export const ePortugues = (v) => normalizarLang(v).startsWith("pt");

// Pontuação de uma voz: pt-BR vale muito; qualidade declarada, depois nomes conhecidos; voz de brincadeira e "compacta" perdem.
export function pontuar(v) {
  const nome = `${v?.name || ""} ${v?.voiceURI || ""}`;
  let p = 0;
  const lang = normalizarLang(v);
  if (lang === "pt-br") p += 100; else if (lang.startsWith("pt")) p += 30; else return -1000;
  if (/premium|prêmio|premio/i.test(nome)) p += 60;
  if (/enhanced|aprimorad|melhorad/i.test(nome)) p += 45;
  if (/compact/i.test(nome)) p -= 10;
  if (/luciana/i.test(nome)) p += 20;
  else if (/felipe/i.test(nome)) p += 15;
  else if (/francisca|antonio|thalita|maria|google português/i.test(nome)) p += 8;
  if (NOVIDADE.test(nome)) p -= 25;
  if (v?.localService) p += 5;  // funciona sem internet
  return p;
}

// Vozes em português, da melhor para a pior (estável: empate mantém a ordem do navegador).
export const listarVozesPt = (vozes) => (vozes || []).map((v, i) => ({ v, i, p: pontuar(v) })).filter((x) => x.p > -1000)
  .sort((a, b) => b.p - a.p || a.i - b.i).map((x) => x.v);

// A preferida (por voiceURI) se ainda existir; senão a melhor pt-BR; senão null (o navegador usa a padrão do idioma).
export function escolherVoz(vozes, preferidaURI = null) {
  const lista = listarVozesPt(vozes);
  return (preferidaURI && lista.find((v) => v.voiceURI === preferidaURI)) || lista[0] || null;
}

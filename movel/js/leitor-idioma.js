// Detecção barata de idioma (sem rede, sem biblioteca): conta palavras funcionais de pt/en/es/fr/de/it. Porte de jarvis/info/leitor_idioma.py.
export const NOMES = { pt: "português", en: "inglês", es: "espanhol", fr: "francês", de: "alemão", it: "italiano" };

const PALAVRAS = {
  pt: "o a os as um uma uns umas de do da dos das em no na nos nas por para com sem que não nao é são mais mas como foi ser tem têm você voce muito também ao aos pela pelo isso este esta está seu sua ou já ainda sobre entre depois",
  en: "the and of to in is are was were for with that this it on as at by from be have has had not but or an they their which will would can about more been said after over also into than who",
  es: "el la los las un una unos unas de del en y que es por con para su sus al lo como más pero fue son está han sobre entre también este esta ese ya muy sin hay sido cuando donde",
  fr: "le la les un une des du de et en est que qui dans pour pas sur au aux avec ce cette ses son sont mais ou il elle nous vous ils plus par été être comme aussi très",
  de: "der die das den dem des und ist ein eine einen einem von zu mit auf für nicht sich auch als bei wie nach aus über wird sind war oder aber noch nur wurde werden dass",
  it: "il lo la i gli le un una uno di del della dei delle e che è in per con su non come più ma anche sono stato questo questa nel nella alla al dal dalla ha hanno sua suo",
};
const CONJUNTOS = Object.fromEntries(Object.entries(PALAVRAS).map(([l, p]) => [l, new Set(p.split(" "))]));
const SINAIS = { pt: "ãõç", es: "ñ¿¡", fr: "èêàûœ", de: "äöüß", it: "ìò" };

// Código do idioma mais provável. Pouca evidência (texto curto/sem palavras funcionais) vale como "pt": não traduz à toa.
export function detectar(texto) {
  const baixo = String(texto || "").toLowerCase().slice(0, 4000);
  const palavras = baixo.match(/[a-zà-ÿñ]+/g) || [];
  if (palavras.length < 4) return "pt";
  const pontos = {};
  for (const [lang, conj] of Object.entries(CONJUNTOS)) pontos[lang] = palavras.filter((p) => conj.has(p)).length;
  for (const [lang, sinais] of Object.entries(SINAIS)) for (const c of sinais) pontos[lang] += baixo.split(c).length - 1 > 0 ? (baixo.split(c).length - 1) * 0.5 : 0;
  let melhor = "pt";
  for (const lang of Object.keys(pontos)) if (pontos[lang] > pontos[melhor]) melhor = lang;
  return pontos[melhor] < 2 ? "pt" : melhor;
}

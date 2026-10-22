// Palavra de ativação lida na TRANSCRIÇÃO ("Jarvis, que horas são"). Porte fiel de jarvis/voice/ativacao.py (extrair_comando): lógica pura,
// sem microfone nem tela. O nome precisa estar no COMEÇO da frase (até 2 palavras antes, como "hey" ou "e aí"): citar a Jarvis no meio de
// uma conversa ou de um vídeo não ativa nada. Texto ouvido é dado de terceiros: aqui só se separa o nome do resto.

const ANTES = new Set(["hey", "hei", "ei", "eia", "ey", "oi", "ola", "opa", "ok", "okay", "o", "e", "ai", "fala", "fale", "veja"]);
const MENCAO = new Set(["e", "eh", "foi", "era", "seria", "tambem"]);  // "o Jarvis é um filme": falar DO Jarvis, não COM ele
const NAO = new Set(["travis", "jarbas", "marvin", "harvey"]);
const INICIAIS = "jgdcy";
// Como o reconhecimento costuma ouvir um "Jarvis" falado em português: só vale no começo da frase.
const OUVIDO_ERRADO = new Set(["avos", "aves", "javis", "arvis", "jarvi"]);
const PALAVRA = /[\p{L}\p{N}_]+/gu;

export const semAcento = (txt) => String(txt).toLowerCase().normalize("NFD").replace(/\p{Mn}/gu, "");

// Equivalente ao SequenceMatcher(None, a, b).ratio() do Python: 2 * (caracteres em blocos comuns) / (tamanho total).
function comuns(a, b, alo, ahi, blo, bhi) {
  let melhor = 0, ia = alo, ib = blo;
  for (let i = alo; i < ahi; i++) {
    for (let j = blo; j < bhi; j++) {
      let k = 0;
      while (i + k < ahi && j + k < bhi && a[i + k] === b[j + k]) k++;
      if (k > melhor) { melhor = k; ia = i; ib = j; }
    }
  }
  if (!melhor) return 0;
  return melhor + comuns(a, b, alo, ia, blo, ib) + comuns(a, b, ia + melhor, ahi, ib + melhor, bhi);
}
export const razao = (a, b) => (a.length + b.length ? (2 * comuns(a, b, 0, a.length, 0, b.length)) / (a.length + b.length) : 1);

export function eJarvis(token) {
  if (OUVIDO_ERRADO.has(token)) return true;
  return !NAO.has(token) && token.length > 0 && INICIAIS.includes(token[0]) && razao(token, "jarvis") >= 0.8;
}

// null = a frase não chama a Jarvis. "" = só a chamou. Senão, o comando que veio depois do nome.
export function extrairComando(texto) {
  texto = String(texto ?? "");
  const palavras = [...texto.matchAll(PALAVRA)].map((m) => [semAcento(m[0]), m.index + m[0].length]);
  for (let i = 0; i < Math.min(3, palavras.length); i++) {
    const [p, fim] = palavras[i];
    if (eJarvis(p)) {
      const resto = texto.slice(fim);
      const seguinte = i + 1 < palavras.length ? palavras[i + 1][0] : "";
      if (MENCAO.has(seguinte) && !/^\s*[,.:;!?\-–—]/.test(resto)) return null;
      return resto.replace(/^[\s,.:;!?\-–—…]+/, "").trim();
    }
    if (!ANTES.has(p)) return null;
  }
  return null;
}

// ── Vocativo no FIM da frase ("oi, boa noite, Jarvis"): como se cumprimenta em português. Não existe no Python: as regras são as de
// docs/CELULAR-INDEPENDENTE.md e os casos compartilhados estão em testes/dados/ativacao_vocativo.json (o PC pode reutilizá-los).
export const MAX_PALAVRAS_VOCATIVO = 8;
// Palavra logo antes do nome que mostra que se fala DO Jarvis ("o Jarvis", "filme Jarvis", "falei com Jarvis"), não COM ele.
const MENCAO_ANTES = new Set(["o", "a", "os", "as", "um", "uma", "do", "da", "dos", "das", "no", "na", "nos", "nas", "ao", "aos", "pelo", "pela", "com", "de", "para", "pra", "pro",
  "sobre", "e", "eh", "sou", "foi", "era", "seria", "somos", "chama", "chamo", "chamado", "chamada", "nome", "meu", "minha", "seu", "sua", "esse", "essa", "este", "esta", "aquele",
  "que", "como", "tipo", "filme", "personagem", "falei", "falou", "disse", "amo", "adoro", "odeio", "conheco", "vi", "ouvi", "li", "assisti"]);
const SO_FIM = /[\s,.:;!?\-–—…]+$/, INICIO_PONTUACAO = /^[\s,.:;!?\-–—…]+/;

const CUMPRIMENTOS = new Set(["oi", "ola", "opa"]);
function saudacaoAntesDoNome(texto) {
  const palavras = [...String(texto).matchAll(PALAVRA)].map((m) => ({ p: semAcento(m[0]), ini: m.index }));
  const i = palavras.findIndex(({ p }) => eJarvis(p));
  const antes = palavras.slice(0, i).map(({ p }) => p);
  if (i < 1 || !(antes.some((p) => CUMPRIMENTOS.has(p)) || antes.join(" ") === "e ai")) return null;
  return texto.slice(0, palavras[i].ini).replace(SO_FIM, "").trim();
}

// Como extrairComando, mas também aceita o nome no FIM de uma frase curta (até 8 palavras), com "por favor" depois dele. Devolve o comando SEM o nome.
export function extrairChamada(texto) {
  const inicio = extrairComando(texto);
  if (inicio === "") return saudacaoAntesDoNome(texto) ?? "";  // "oi Jarvis" não é só uma chamada: é um cumprimento e merece resposta
  if (inicio !== null) return inicio;
  texto = String(texto ?? "");
  const palavras = [...texto.matchAll(PALAVRA)].map((m) => ({ p: semAcento(m[0]), ini: m.index, fim: m.index + m[0].length }));
  if (palavras.length < 2 || palavras.length > MAX_PALAVRAS_VOCATIVO) return null;
  const k = palavras.length - 1;
  const cortesia = palavras[k].p === "pfv" ? 1 : palavras[k - 1]?.p === "por" && palavras[k].p === "favor" ? 2 : 0;
  const i = k - cortesia, nome = palavras[i];
  if (i < 1 || OUVIDO_ERRADO.has(nome.p) || !eJarvis(nome.p) || MENCAO_ANTES.has(palavras[i - 1].p)) return null;
  const cabeca = texto.slice(0, nome.ini).replace(SO_FIM, ""), cauda = texto.slice(nome.fim).replace(INICIO_PONTUACAO, "");
  return `${cabeca} ${cauda}`.replace(SO_FIM, "").trim();
}

// Letras minúsculas sem acento nem pontuação: para comparar o que foi ouvido com o que a própria Jarvis está falando (eco).
export const forma = (txt) => semAcento(txt).replace(/[^\p{L}\p{N}]+/gu, " ").trim();
export const eEcoDe = (ouvido, falado) => { const o = forma(ouvido); return Boolean(o) && forma(falado).includes(o); };

// Pedidos de controle da própria escuta ("Jarvis, para", "Jarvis, tchau"): tratados aqui, sem gastar uma resposta da IA.
export function comandoDeControle(comando) {
  const t = forma(comando);
  if (/^(tchau|desligar|desliga|encerrar|pode desligar)( o microfone| a escuta| a conversa| conversa)?$/.test(t)) return "desligar";
  if (/^(para|pare|parar|chega|silencio|cala a boca|pode parar|esquece)( de falar| a fala)?$/.test(t)) return "parar-fala";
  return null;
}

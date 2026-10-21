// Nota de 0 a 100 de cada artigo, sempre com os motivos. Porte de jarvis/radar/pontuacao.py.
//   +40 relevância (palavras-chave do nicho; o título pesa mais que o resumo)   +20 nota da fonte (0–10 × 2)
//   +15 ineditismo (nenhum título parecido no histórico recente)                +15 impacto (dinheiro, lei, tecnologia central)
//   +10 frescor (linear dentro da janela)                                       -30 clickbait, listicle ou release disfarçado
import { parecidos } from "./radar-dedup.js";
import { semAcento } from "./radar-texto.js";

const IMPACTO = ["lei", "decreto", "aprova", "aprovou", "proibe", "regulament", "multa", "bilhao", "bilhoes", "milhoes", "lanca", "lancou", "anuncia", "anunciou",
  "acordo", "fusao", "aquisicao", "compra", "falencia", "vazamento", "ataque", "investigacao", "decisao", "recorde", "queda", "alta", "juros", "inflacao"];
const CLICKBAIT = new RegExp("voce nao vai acreditar|veja o que|saiba (o que|como|quem)|descubra|confira|chocante|bomba|inacreditavel|"
  + "^\\s*(top\\s*)?\\d+\\s+(coisas|motivos|dicas|jeitos|formas|razoes|segredos|erros|filmes|series|apps)\\b|"
  + "\\b\\d+\\s+(coisas|motivos|dicas|jeitos|formas|razoes|segredos)\\b|isso (vai|muda)|nunca mais|em (apenas )?\\d+ passos|"
  + "comunicado a imprensa|press release|release", "i");
const PATROCINADO = /publieditorial|patrocinad|conteudo (de marca|publicitario)|\[publi\]|oferta|cupom|promocao|desconto/i;

// Arredondamento do Python (metade vai para o par), para dar a mesma nota do PC.
const arredondar = (x) => { const r = Math.round(x); return Math.abs(x % 1) === 0.5 && r % 2 ? r - 1 : r; };

export function tem(texto, termo) {
  termo = semAcento(termo).trim();
  return Boolean(termo) && new RegExp(`(?<![a-z0-9])${termo.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`).test(texto);
}

export const ehPatrocinado = (a) => PATROCINADO.test(semAcento(`${a.titulo} ${a.resumo.slice(0, 120)}`));

// quando e agora em SEGUNDOS. Devolve [nota, motivos].
export function pontuar(artigo, palavrasChave, entidades, janelaHoras, titulosRecentes, agora = Date.now() / 1000) {
  const titulo = semAcento(artigo.titulo), resumo = semAcento(artigo.resumo);
  let pontos = 0;
  const motivos = [];
  const noTitulo = palavrasChave.filter((p) => tem(titulo, p));
  const noResumo = palavrasChave.filter((p) => !noTitulo.includes(p) && tem(resumo, p));
  const relevancia = Math.min(40, 16 * noTitulo.length + 8 * noResumo.length);
  if (relevancia) { pontos += relevancia; motivos.push("bate com: " + [...noTitulo, ...noResumo].join(", ")); }
  pontos += arredondar(Math.max(0, Math.min(10, artigo.notaFonte)) * 2);
  motivos.push(`fonte ${artigo.fonte} (nota ${artigo.notaFonte})`);
  if (!titulosRecentes.some((antigo) => parecidos(artigo.titulo, antigo))) { pontos += 15; motivos.push("assunto inédito"); }
  const texto = `${titulo} ${resumo}`;
  const impacto = IMPACTO.filter((w) => tem(texto, w)), seguidas = entidades.filter((e) => tem(texto, e));
  const ganho = Math.min(15, 5 * impacto.length + 8 * seguidas.length);
  if (ganho) { pontos += ganho; motivos.push("impacto: " + [...seguidas, ...impacto.slice(0, 3)].join(", ")); }
  if (artigo.quando) pontos += arredondar(10 * Math.max(0, 1 - Math.max(0, (agora - artigo.quando) / 3600) / Math.max(1, janelaHoras)));
  if (CLICKBAIT.test(titulo)) { pontos -= 30; motivos.push("cara de clickbait/lista/release (-30)"); }
  return [Math.max(0, Math.min(100, pontos)), motivos];
}

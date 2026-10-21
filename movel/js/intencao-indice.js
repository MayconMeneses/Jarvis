// Índice de intenções (sem IA). Espelho de jarvis/local/casador.py: cada frase-exemplo, rótulo e palavra-chave de um alvo (comando do motor
// ou assunto do app) é um "documento"; a nota do alvo é a do seu melhor documento. A nota mistura BM25 (palavras raras pesam mais),
// cobertura das palavras raras da pergunta e trigramas de letras. Erros de digitação e de escuta são corrigidos contra o vocabulário.
import { corrigir, jaccard, palavras, radical, termos, trigramas } from "./intencao-texto.js";

export const K1 = 1.4, B = 0.6;
// Verbos e palavras de pergunta que aparecem em quase toda frase de ajuda: valem pouco para distinguir o assunto.
const GENERICAS = new Set(("como onde configurar configuro usar uso usa ver vejo mostrar funciona precisa preciso fazer faz faco ficar fica ter tem "
  + "quero posso pode jarvis voce vc colocar ligar ativar mudar trocar").split(" ").map(radical));
const INSTRUCIONAL = new Set(["como", "onde", "porque", "posso", "da", "ha", "existe", "tem"]);

export class Indice {
  // alvos: [{ id, tipo: "app" | "comando", rotulo, exemplos: [frases], palavras: [palavras-chave] }]
  constructor(alvos) {
    const brutos = [];
    for (const a of alvos) {
      for (const f of a.exemplos || []) brutos.push([a, f, 1.0]);
      if (a.rotulo) brutos.push([a, a.rotulo, 0.97]);
      for (const p of a.palavras || []) brutos.push([a, p, 0.92]);
    }
    this.alvos = alvos;
    this.vocabulario = new Set(["jarvis"]);
    for (const [, texto] of brutos) for (const p of palavras(texto)) if (p.length >= 4) this.vocabulario.add(p);
    this.docs = brutos.map(([alvo, texto, peso]) => ({ alvo, texto, peso, termos: termos(texto), tri: trigramas(texto) }));
    const freq = new Map();
    for (const d of this.docs) for (const t of new Set(d.termos)) freq.set(t, (freq.get(t) || 0) + 1);
    const n = this.docs.length;
    this.idfs = new Map([...freq].map(([t, f]) => [t, Math.log(1 + (n - f + 0.5) / (f + 0.5))]));
    this.idfDesconhecido = Math.log(1 + n + 0.5);
    this.medio = this.docs.reduce((s, d) => s + d.termos.length, 0) / Math.max(1, n);
  }

  _idf(t) { const base = this.idfs.get(t) ?? this.idfDesconhecido; return GENERICAS.has(t) ? base * 0.35 : base; }

  _bm25(consulta, termosDoc) {
    const tf = new Map();
    for (const t of termosDoc) tf.set(t, (tf.get(t) || 0) + 1);
    let total = 0;
    for (const t of new Set(consulta)) {
      const f = tf.get(t);
      if (f) total += (this._idf(t) * f * (K1 + 1)) / (f + K1 * (1 - B + (B * termosDoc.length) / this.medio));
    }
    return total;
  }

  _pontuar(consulta, tri, doc) {
    if (!consulta.length || !doc.termos.length) return 0;
    const maximo = this._bm25(consulta, consulta) || 1;
    const bm = Math.min(1, this._bm25(consulta, doc.termos) / maximo);
    const unicos = [...new Set(consulta)], pesoTotal = unicos.reduce((s, t) => s + this._idf(t), 0) || 1;
    const cobertura = unicos.filter((t) => doc.termos.includes(t)).reduce((s, t) => s + this._idf(t), 0) / pesoTotal;
    return doc.peso * (0.45 * bm + 0.4 * cobertura + 0.15 * jaccard(tri, doc.tri));
  }

  // Candidatos ordenados: [{ id, tipo, alvo, nota }]. Um por alvo (a nota do melhor documento).
  buscar(frase, quantos = 3) {
    const pal = palavras(frase).map((p) => corrigir(p, this.vocabulario));
    const corrigido = pal.join(" "), consulta = termos(corrigido);
    if (!consulta.length) return [];
    const tri = trigramas(corrigido), melhor = new Map();
    for (const d of this.docs) {
      const nota = this._pontuar(consulta, tri, d);
      const n = nota * (d.alvo.peso ?? 1);  // peso < 1: alvo que serve menos a este aparelho (assunto só do PC)
      if (n > 0 && (!melhor.has(d.alvo.id) || n > melhor.get(d.alvo.id).nota)) melhor.set(d.alvo.id, { id: d.alvo.id, tipo: d.alvo.tipo, alvo: d.alvo, nota: n });
    }
    const instrucional = pal.length > 0 && (INSTRUCIONAL.has(pal[0]) || pal.slice(0, 2).join(" ") === "por que");
    let lista = [...melhor.values()];
    if (instrucional) lista = lista.map((c) => ({ ...c, nota: c.nota * (c.tipo === "app" ? 1.08 : 0.88) }));  // "como ver minha cota": quer o passo a passo
    return lista.sort((a, b) => b.nota - a.nota).slice(0, quantos);
  }
}

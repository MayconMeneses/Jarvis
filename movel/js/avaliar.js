// Régua do cérebro do aparelho (mesmo desenho de jarvis/llm/avaliar.py): tarefas pequenas de JavaScript com testes escondidos.
// O código que o modelo escreve roda só no ambiente isolado (sandbox.js); a nota (0 a 100) é guardada com a data e o modelo.
import { isoData } from "./util.js";

export const TAREFAS = [
  ["ehPar", "ehPar(n) devolve true se n é par", [[[4], true], [[7], false], [[0], true]]],
  ["somaLista", "somaLista(xs) devolve a soma dos números do array", [[[[1, 2, 3]], 6], [[[]], 0]]],
  ["maior", "maior(xs) devolve o maior número do array", [[[[3, 9, 2]], 9], [[[-5, -1]], -1]]],
  ["palindromo", "palindromo(s) devolve true se o texto lido de trás para frente é igual (ignore maiúsculas)", [[["Ana"], true], [["casa"], false]]],
  ["fatorial", "fatorial(n) devolve n! (fatorial(0) é 1)", [[[5], 120], [[0], 1]]],
];
export const INTERVALO_DIAS = 7;
const META = "avaliacoes";

export const codigoDe = (resposta) => (/```[\w+-]*\n([\s\S]*?)```/.exec(resposta)?.[1] ?? resposta).trim();

// Arquivos para o sandbox: a solução (com a função exportada, mesmo que o modelo esqueça) e o teste com os casos escondidos.
export function arquivosDaTarefa(funcao, codigo, casos) {
  const solucao = `${codigo}\nif (typeof ${funcao} === "function") module.exports.${funcao} = ${funcao};\n`;
  const teste = `const test = require("node:test");\nconst assert = require("node:assert");\nconst { ${funcao} } = require("./solucao.js");\n`
    + casos.map(([args, esperado], i) => `test("caso ${i + 1}", () => assert.deepEqual(${funcao}(...${JSON.stringify(args)}), ${JSON.stringify(esperado)}));`).join("\n");
  return { "solucao.js": solucao, "solucao.test.js": teste };
}

export async function avaliar({ conversa, rodar, tarefas = TAREFAS, relogio = () => Date.now() }) {
  const inicio = relogio(), detalhes = {};
  for (const [funcao, enunciado, casos] of tarefas) {
    const pedido = `Escreva em JavaScript a função ${enunciado}. Responda só com o código, em um bloco, sem usar import nem export.`;
    try {
      const codigo = codigoDe(await conversa([{ role: "user", content: pedido }]));
      const r = await rodar({ linguagem: "javascript", arquivos: arquivosDaTarefa(funcao, codigo, casos), principal: "solucao.js", modo: "testar" });
      detalhes[funcao] = Boolean(r?.ok);
    } catch (e) { detalhes[funcao] = false; }
  }
  const acertos = Object.values(detalhes).filter(Boolean).length;
  return { acertos, total: tarefas.length, nota: Math.round((100 * acertos) / tarefas.length), detalhes, segundos: Math.round((relogio() - inicio) / 1000) };
}

export class Avaliador {
  constructor({ memoria, conversa, rodar, disponivel, rotulo = () => "aparelho", relogio = () => new Date() }) { Object.assign(this, { memoria, conversa, rodar, disponivel, rotulo, relogio }); this.ocupado = false; }

  async historico() { return (await this.memoria.meta(META)) || []; }

  async vencida() {
    const [ultima] = await this.historico();
    return !ultima || this.relogio() - new Date(ultima.quando) >= INTERVALO_DIAS * 86400000;
  }

  // Roda a avaliação e guarda a nota. Sem cérebro (aparelho ou nuvem) não roda. Devolve o texto do resultado.
  async executar() {
    if (this.ocupado) return "Já estou avaliando; aguarde o resultado.";
    if (!(await this.disponivel())) return "Para avaliar eu preciso de um cérebro ligado: baixe e ligue o modelo do aparelho (aba Cérebro) ou cadastre uma chave de nuvem.";
    this.ocupado = true;
    try {
      const modelo = this.rotulo(), anteriores = await this.historico();
      const r = await avaliar({ conversa: this.conversa, rodar: this.rodar, relogio: () => this.relogio().getTime() });
      await this.memoria.definirMeta(META, [{ quando: this.relogio().toISOString(), modelo, nota: r.nota, acertos: r.acertos, total: r.total, detalhes: r.detalhes }, ...anteriores].slice(0, 30));
      const erros = Object.entries(r.detalhes).filter(([, ok]) => !ok).map(([f]) => f);
      const antes = anteriores.find((a) => a.modelo === modelo);
      return `**Avaliação do cérebro (${modelo}):** ${r.acertos} de ${r.total} tarefas certas, nota ${r.nota}/100, em ${r.segundos} s.`
        + (erros.length ? ` Errou: ${erros.join(", ")}.` : " Acertou tudo.")
        + (antes ? ` Na avaliação anterior (${isoData(new Date(antes.quando))}) a nota foi ${antes.nota}.` : " Esta é a primeira avaliação deste cérebro.");
    } finally { this.ocupado = false; }
  }

  async resumo() {
    const [u] = await this.historico();
    if (!u) return 'Ainda não avaliei o cérebro. Toque em Avaliar agora ou diga "avaliar cérebro".';
    return `Última avaliação (${isoData(new Date(u.quando))}, ${u.modelo}): nota ${u.nota}/100, ${u.acertos} de ${u.total} tarefas certas.`;
  }
}

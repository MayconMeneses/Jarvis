// Criar sistemas "pensando" (mesmo fluxo do PC, jarvis/llm/pensar.py): planeja os arquivos, escreve um por vez, confere cada um,
// roda os testes NO SANDBOX e pede correção (até 2 rodadas). O modelo é uma fonte não confiável: o que ele escreve é só texto
// guardado na Oficina; nada executa sozinho aqui além dos testes que o próprio clique em "Criar com IA" autoriza, sempre no sandbox.
import { caminhoSeguro, MAX_ARQUIVOS, MAX_CHARS } from "./oficina-espaco.js";

export const TENTATIVAS = 3, MAX_PLANO = 7;
const DICA_TESTE_PY = " Nos testes use poucos casos com números fáceis de conferir de cabeça (ex.: soma 2 e 3 dá 5) e compare decimais com pytest.approx.";
const DICA_JS = " JavaScript no estilo CommonJS: use require() e module.exports (sem import/export). Testes usam require('node:test') e require('node:assert').";
const LINHA_PLANO = /^[\s>*\-\d.)]*`?([\p{L}\p{N}_][\p{L}\p{N}_./\\-]*\.\w{1,5})`?\s*[:\-–—]\s*(.+)$/u;
const BLOCO = /```[\w+-]*\n([\s\S]*?)```/;

const nomeBase = (c) => c.split("/").at(-1);
export const eTeste = (c) => /^test|\.test\.|_test\./.test(nomeBase(c)) && /\.(py|js)$/.test(c);
const semQuebras = (t) => t.replace(/^\n+|\n+$/g, "");

export function extrairCodigo(resposta) {
  const achado = BLOCO.exec(resposta);
  if (achado) return semQuebras(achado[1]);
  return semQuebras(String(resposta).trim().replace(/^```[\w+-]*\n?|\n?```$/g, ""));
}

export function interpretarPlano(texto, limite = 8) {
  const plano = [];
  for (const linha of String(texto).split(/\r?\n/)) {
    const achado = LINHA_PLANO.exec(linha.trim());
    if (!achado) continue;
    let caminho;
    try { caminho = caminhoSeguro(achado[1]); } catch (e) { continue; }
    if (caminho.toLowerCase() !== "readme.md" && !plano.some(([c]) => c === caminho)) plano.push([caminho, achado[2].trim()]);
  }
  return plano.slice(0, limite);
}

// Só olha a sintaxe, sem executar nada (new Function compila e não roda). Se a página proíbe isso (política de segurança), pula:
// os testes no sandbox pegam o erro do mesmo jeito.
export function sintaxeJs(conteudo) {
  try { new Function("require", "module", "exports", conteudo); return null; } catch (e) {
    if (e instanceof EvalError) return null;
    const dica = /^\s*(import|export)\b/m.test(conteudo) ? " (use require/module.exports, não import/export)" : "";
    return `erro de sintaxe JavaScript: ${e.message}${dica}`;
  }
}

// null = parece válido; senão, o erro para devolver ao modelo. `conferirPython` é opcional (precisa do Pyodide); sem ele, Python não é checado.
export async function conferir(caminho, conteudo, { conferirPython } = {}) {
  if (!conteudo.trim()) return "o arquivo ficou vazio";
  const ext = (/\.[^./]+$/.exec(caminho) || [""])[0].toLowerCase();
  if (ext === ".json") { try { JSON.parse(conteudo); } catch (e) { return `JSON inválido: ${e.message}`; } }
  else if (ext === ".js") return sintaxeJs(conteudo);
  else if (ext === ".py" && conferirPython) return (await conferirPython(caminho, conteudo)) || null;
  return null;
}

const msg = (role, content) => ({ role, content });

export async function planejar(descricao, conversa, sistema) {
  const pedido = `Projeto: ${descricao}\n\nListe os arquivos necessários (no máximo ${MAX_PLANO}, simples, com testes). Cada função fica em UM só arquivo. `
    + "Em JavaScript os testes se chamam <modulo>.test.js; em Python, test_<modulo>.py; sempre importam do módulo. "
    + "Uma linha por arquivo no formato `caminho: o que faz`. Sem explicações e sem README.";
  const plano = interpretarPlano(await conversa([msg("system", sistema), msg("user", pedido)]), MAX_PLANO);
  if (!plano.length) throw new Error("o modelo não conseguiu planejar os arquivos; descreva o sistema com mais detalhes");
  return plano;
}

// [conteudo, aviso]: o aviso só existe se, mesmo após as tentativas, o arquivo continuou com problema.
export async function escreverArquivo(caminho, funcao, descricao, plano, prontos, conversa, sistema, opcoes = {}) {
  const visao = plano.map(([c, f]) => `- ${c}: ${f}`).join("\n");
  const anteriores = Object.entries(prontos).slice(-2).map(([c, t]) => `Arquivo ${c}:\n${t.slice(0, 600)}`).join("\n\n");
  const dica = (nomeBase(caminho).startsWith("test_") ? DICA_TESTE_PY : "") + (caminho.endsWith(".js") ? DICA_JS : "");
  const mensagens = [msg("system", sistema), msg("user", `Projeto: ${descricao}\nArquivos do projeto:\n${visao}\n\n${anteriores}\n\n`
    + `Escreva o arquivo ${caminho} (${funcao}). Importe do projeto tudo que usar de outros arquivos e não repita o que eles já definem. `
    + "Responda SÓ com o conteúdo, dentro de um bloco de código." + dica)];
  let erro = null, conteudo = "";
  for (let i = 0; i < TENTATIVAS; i++) {
    conteudo = extrairCodigo(await conversa(mensagens));
    erro = await conferir(caminho, conteudo, opcoes);
    if (erro === null) return [conteudo, null];
    mensagens.push(msg("assistant", "```\n" + conteudo + "\n```"),
      msg("user", `O arquivo tem um problema: ${erro}. Corrija e envie o arquivo completo de novo, em um bloco de código.`));
  }
  return [conteudo, `${caminho}: ${erro} (revise antes de usar)`];
}

// Roda os testes gerados no sandbox. `rodar(linguagem, arquivos)` -> {ok, estourou, saida}. null = passou ou não deu para testar; senão { erro, ext }.
export async function rodarTestes(arquivos, { rodar, testarPython = false } = {}) {
  if (!rodar) return null;
  for (const [linguagem, ext] of [["javascript", ".js"], ["python", ".py"]]) {
    if (linguagem === "python" && !testarPython) continue;
    if (!Object.keys(arquivos).some((c) => c.endsWith(ext) && eTeste(c))) continue;
    const r = await rodar(linguagem, arquivos);
    if (r.estourou) return { erro: `os testes (${linguagem}) demoraram demais`, ext };
    if (!r.ok) return { erro: String(r.saida || r.texto || "os testes falharam").trim().slice(-1500), ext };
  }
  return null;
}

// Pede ao modelo para corrigir o arquivo que o teste acusa (o de código antes do de teste). true se mudou algo.
export async function reparar(resultado, falha, descricao, conversa, sistema, rodada = 0, opcoes = {}) {
  const { erro, ext } = falha;
  const doTipo = Object.keys(resultado.arquivos).filter((c) => c.endsWith(ext));
  const codigo = doTipo.filter((c) => !eTeste(c)), testes = doTipo.filter(eTeste);
  const caminho = (rodada ? testes : codigo.filter((c) => erro.includes(c)).concat(codigo))[0] || doTipo[0];
  if (!caminho) return false;
  const fontes = doTipo.map((c) => `${c}:\n${resultado.arquivos[c].slice(0, 1200)}`).join("\n\n");
  const pedido = `Projeto: ${descricao}\nOs testes falharam:\n${erro}\n\nArquivos:\n${fontes}\n\n`
    + `Corrija o arquivo ${caminho} para os testes passarem (o erro pode estar no código ou no teste; corrija só este arquivo). Responda SÓ com o arquivo completo, em um bloco de código.`;
  const novo = extrairCodigo(await conversa([msg("system", sistema), msg("user", pedido)]));
  if (novo !== resultado.arquivos[caminho] && (await conferir(caminho, novo, opcoes)) === null) { resultado.arquivos[caminho] = novo; return true; }
  return false;
}

export function leiame(nome, descricao, plano) {
  const itens = plano.map(([c, f]) => `- \`${c}\`: ${f}`).join("\n");
  return `# ${nome}\n\n${descricao}\n\n## Arquivos\n${itens}\n\n> Gerado pela Jarvis com IA. Leia o código e rode os testes antes de confiar nele.\n`;
}

// Só caminhos e tamanhos que a Oficina aceita; o que não serve vira aviso em vez de derrubar tudo.
function validar(arquivos, avisos) {
  const limpos = {};
  for (const [c, t] of Object.entries(arquivos)) {
    try {
      if (t.length > MAX_CHARS) throw new Error(`grande demais (máximo ${MAX_CHARS} caracteres)`);
      if (Object.keys(limpos).length >= MAX_ARQUIVOS) throw new Error("arquivos demais");
      limpos[caminhoSeguro(c)] = t;
    } catch (e) { avisos.push(`${c}: não foi guardado (${e.message})`); }
  }
  if (!Object.keys(limpos).length) throw new Error("nenhum arquivo para criar");
  return limpos;
}

// conversa: async (mensagens) => texto (o cérebro do aparelho ou da nuvem, escolhido pelo app).
// opcoes: { sistema, status, rodar, testarPython, conferirPython }. Devolve { arquivos, avisos, linguagem, principal, testes }.
export async function criar(nome, descricao, conversa, { sistema = "", status = () => {}, rodar, testarPython = false, conferirPython } = {}) {
  const opcoes = { conferirPython };
  status("Planejando os arquivos…");
  const plano = await planejar(descricao, conversa, sistema);
  const resultado = { arquivos: {}, avisos: [] };
  for (const [i, [caminho, funcao]] of plano.entries()) {
    status(`Escrevendo ${caminho} (${i + 1} de ${plano.length})…`);
    const [conteudo, aviso] = await escreverArquivo(caminho, funcao, descricao, plano, resultado.arquivos, conversa, sistema, opcoes);
    resultado.arquivos[caminho] = conteudo;
    if (aviso) resultado.avisos.push(aviso);
  }
  const testar = () => rodarTestes(resultado.arquivos, { rodar, testarPython });
  if (rodar) status("Rodando os testes no sandbox…");
  let falha = await testar();
  for (let rodada = 0; rodada < 2 && falha !== null; rodada++) {
    status(`Os testes falharam; pedindo uma correção (${rodada + 1} de 2)…`);
    if (!(await reparar(resultado, falha, descricao, conversa, sistema, rodada, opcoes))) break;
    falha = await testar();
  }
  if (falha !== null) resultado.avisos.push(`os testes gerados ainda falham: ${falha.erro.split("\n").filter(Boolean).at(-1).slice(0, 160)} (revise antes de usar)`);
  resultado.arquivos["README.md"] = leiame(nome, descricao, plano);
  const arquivos = validar(resultado.arquivos, resultado.avisos);
  const js = Object.keys(arquivos).some((c) => c.endsWith(".js")), py = Object.keys(arquivos).some((c) => c.endsWith(".py"));
  const linguagem = js && !py ? "javascript" : "python";
  const principal = Object.keys(arquivos).find((c) => c.endsWith(linguagem === "python" ? ".py" : ".js") && !eTeste(c)) || "";
  return { arquivos, avisos: resultado.avisos, linguagem, principal, testes: falha === null ? "" : falha.erro };
}

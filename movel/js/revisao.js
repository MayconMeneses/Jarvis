// Revisão de código e de diffs (as mesmas regras do PC): só lê o que foi colado, nunca executa nada.
const ALTA = "alta", MEDIA = "média", BAIXA = "baixa";
const LIMITE_LINHA = 140, LIMITE_DIFF = 400;

// Padrões de risco montados por partes para este arquivo não ser acusado por si mesmo.
const RISCOS = [
  [new RegExp("\\b(ev" + "al|ex" + "ec)\\s*\\("), ALTA, "Execução de código dinâmico", "Evite eval/exec; use um parser (JSON.parse, ast.literal_eval) ou uma tabela de funções permitidas."],
  [/shell\s*=\s*True/, ALTA, "Comando de shell montado como texto", "Passe uma lista de argumentos e shell=False, para o texto do usuário não virar comando."],
  [/verify\s*=\s*False|rejectUnauthorized\s*:\s*false/, ALTA, "Verificação de certificado desligada", "Mantenha a verificação TLS ligada; trate o certificado em vez de ignorá-lo."],
  [/\bf["'][^"'\n]*\b(select\b.*\bfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b|\b(select\b.*\bfrom|insert\s+into|delete\s+from)\b[^\n]*(["']\s*\+\s*\w|\.format\(|["']\s*%\s*\w)|`[^`\n]*\b(select\b.*\bfrom|insert\s+into|delete\s+from)\b[^`\n]*\$\{/i,
    ALTA, "SQL montado com texto", "Use consultas parametrizadas (?, %s ou :nome) em vez de juntar o valor no texto da consulta."],
  [/\.innerHTML\s*=|document\.write\s*\(|dangerouslySetInnerHTML/, MEDIA, "HTML inserido sem filtro", "Use textContent ou crie os elementos pelo DOM; HTML de fora pode carregar script (XSS)."],
  [/^\s*except\s*:\s*$|except\s+Exception\s*:\s*(pass)?\s*$/, MEDIA, "Exceção engolida", "Capture o erro específico e registre ou trate; um except vazio esconde defeitos."],
  [/(password|senha|token|secret)\w*\s*[,)]?\s*["'].*%s|log\w*\.\w+\(.*(password|senha|token)/i, MEDIA, "Possível dado sensível no log", "Nunca registre senhas, tokens ou chaves; registre só identificadores."],
  [/\b(breakpoint\(\)|pdb\.set_trace|debugger;)/, MEDIA, "Depurador esquecido", "Remova a parada de depuração antes de integrar."],
  [/\b(TODO|FIXME|XXX|HACK)\b/, BAIXA, "Pendência marcada", "Resolva ou transforme em uma tarefa rastreável antes de integrar."],
  [/^\s*(print\(|console\.log\()/, BAIXA, "Saída de depuração", "Use o sistema de logs (logging/console.error) ou remova."],
];
const SEGREDOS = [/AKIA[0-9A-Z]{16}/, /-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/, /gh[pousr]_[A-Za-z0-9]{36,}/, /AIza[0-9A-Za-z_-]{35}/, /sk-[A-Za-z0-9]{20,}/,
  /\b(api[_-]?key|secret|token|passw(or)?d|senha)\w*\s*[:=]\s*["'][A-Za-z0-9_\-/+=.]{12,}["']/i];
const PLACEHOLDER = /(changeme|exemplo|example|your|seu[_-]|xxx|<|\$\{|os\.environ|getenv|process\.env|placeholder|dummy)/i;
const TESTE = /(^|\/)(tests?|__tests__|spec)\/|test_[^/]*\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$/;
const CODIGO = /\.(py|js|jsx|ts|tsx|go|java|cs|php|rb|rs|kt)$/;

function linhasAdicionadas(texto) {
  const linhas = texto.split("\n");
  if (!linhas.some((l) => l.startsWith("@@") || l.startsWith("+++ "))) return { adicionadas: linhas.map((l, i) => ["trecho", i + 1, l]), arquivos: new Set() };
  const adicionadas = [], arquivos = new Set();
  let arquivo = "?", numero = 0;
  for (const linha of linhas) {
    let m;
    if ((m = /^\+\+\+ (?:b\/)?(.+?)(?:\t.*)?$/.exec(linha))) { arquivo = m[1]; arquivos.add(arquivo); }
    else if ((m = /^@@ -\d+(?:,\d+)? \+(\d+)/.exec(linha))) numero = +m[1];
    else if (linha.startsWith("+") && !linha.startsWith("+++")) { adicionadas.push([arquivo, numero, linha.slice(1)]); numero++; }
    else if (!/^[-\\]/.test(linha)) numero++;
  }
  return { adicionadas, arquivos };
}

export function revisar(texto) {
  const { adicionadas, arquivos } = linhasAdicionadas(texto);
  const achados = [];
  for (const [arquivo, linha, conteudo] of adicionadas) {
    for (const [regex, gravidade, regra, sugestao] of RISCOS) if (regex.test(conteudo)) achados.push({ gravidade, arquivo, linha, regra, sugestao, trecho: conteudo.trim().slice(0, 100) });
    if (SEGREDOS.some((r) => r.test(conteudo)) && !PLACEHOLDER.test(conteudo)) {
      achados.push({ gravidade: ALTA, arquivo, linha, regra: "Possível segredo no código", sugestao: "Tire a chave do código: use variável de ambiente ou cofre, e troque a chave se ela já foi enviada.", trecho: "(valor oculto)" });
    }
    if (conteudo.length > LIMITE_LINHA) achados.push({ gravidade: BAIXA, arquivo, linha, regra: `Linha com ${conteudo.length} caracteres`, sugestao: "Quebre a linha ou extraia uma função.", trecho: conteudo.trim().slice(0, 60) + "…" });
  }
  const lista = [...arquivos];
  if (lista.length) {
    const codigo = lista.filter((a) => CODIGO.test(a) && !TESTE.test(a));
    if (codigo.length && !lista.some((a) => TESTE.test(a))) achados.push({ gravidade: MEDIA, arquivo: "(diff)", linha: 0, regra: "Código alterado sem teste", sugestao: "Inclua ou atualize um teste que cubra a mudança.", trecho: codigo.slice(0, 3).join(", ") });
    if (adicionadas.length > LIMITE_DIFF) achados.push({ gravidade: BAIXA, arquivo: "(diff)", linha: 0, regra: `Diff grande (${adicionadas.length} linhas adicionadas)`, sugestao: "Mudanças pequenas são revisadas melhor: divida em partes com um objetivo cada.", trecho: "" });
  }
  const ordem = { [ALTA]: 0, [MEDIA]: 1, [BAIXA]: 2 };
  achados.sort((a, b) => ordem[a.gravidade] - ordem[b.gravidade] || (a.arquivo < b.arquivo ? -1 : a.arquivo > b.arquivo ? 1 : 0) || a.linha - b.linha);
  return { achados, resumo: { adicionadas: adicionadas.length, arquivos: lista.sort() } };
}

export function relatorio(texto) {
  const { achados, resumo } = revisar(texto);
  const cabeca = resumo.arquivos.length ? `**Revisão do diff** (${resumo.arquivos.length} arquivo(s), ${resumo.adicionadas} linhas adicionadas)` : `**Revisão do trecho** (${resumo.adicionadas} linhas)`;
  if (!achados.length) return cabeca + "\nNão achei problemas conhecidos nas regras que eu verifico. Isso não substitui ler o código: confira a lógica, os casos de borda e os testes.";
  const marca = { [ALTA]: "🔴", [MEDIA]: "🟠", [BAIXA]: "⚪" };
  const linhas = [cabeca, `${achados.length} ponto(s) para olhar:`];
  for (const a of achados.slice(0, 25)) {
    const onde = a.linha ? `${a.arquivo}:${a.linha}` : a.arquivo;
    linhas.push(`- ${marca[a.gravidade]} **${a.regra}** (${a.gravidade}) em \`${onde}\`` + (a.trecho ? `: \`${a.trecho}\`` : "") + `\n  → ${a.sugestao}`);
  }
  if (achados.length > 25) linhas.push(`- … e mais ${achados.length - 25} ponto(s).`);
  linhas.push("\n_São sinais automáticos, não um veredito: confirme cada um lendo o código._");
  return linhas.join("\n");
}

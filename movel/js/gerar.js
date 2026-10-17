// Geradores de artefatos de engenharia (texto): tabela SQL, ADR, história de usuário, OpenAPI, CI, Dockerfile, .editorconfig.
import { isoData } from "./util.js";

const TIPOS_SQL = { texto: "TEXT", inteiro: "INTEGER", numero: "REAL", decimal: "REAL", data: "TEXT", booleano: "INTEGER", bool: "INTEGER" };

function idSeguro(nome) {
  const limpo = String(nome).trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "");
  if (!limpo || /^\d/.test(limpo)) throw new Error(`nome inválido: ${nome}`);
  return limpo;
}

export function esquemaSql(tabela, campos = {}, relacoes = {}) {
  const nome = idSeguro(tabela);
  const linhas = ["  id INTEGER PRIMARY KEY AUTOINCREMENT"];
  for (const [campo, tipo] of Object.entries(campos)) linhas.push(`  ${idSeguro(campo)} ${TIPOS_SQL[String(tipo).toLowerCase()] || "TEXT"}`);
  for (const [campo, pai] of Object.entries(relacoes)) linhas.push(`  ${idSeguro(campo)} INTEGER NOT NULL REFERENCES ${idSeguro(pai)}(id)`);
  linhas.push("  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP");
  const indices = Object.keys(relacoes).map((c) => `\nCREATE INDEX idx_${nome}_${idSeguro(c)} ON ${nome}(${idSeguro(c)});`).join("");
  return `CREATE TABLE ${nome} (\n${linhas.join(",\n")}\n);${indices}`;
}

export const adr = (titulo, contexto, decisao, consequencias = "", numero = 1, hoje = new Date()) =>
  `# ADR ${String(numero).padStart(4, "0")}: ${titulo}\n\n- **Data:** ${isoData(hoje)}\n- **Status:** proposta\n\n## Contexto\n${contexto}\n\n## Decisão\n${decisao}\n\n`
  + `## Consequências\n${consequencias || "A preencher: o que melhora, o que piora e o que passa a ser obrigatório."}\n`;

export const historiaUsuario = (papel, quero, para, criterios = ["Dado um contexto inicial, quando a ação acontece, então o resultado esperado é visível."]) =>
  `**Como** ${papel}, **quero** ${quero}, **para** ${para}.\n\n**Critérios de aceite:**\n${criterios.map((c) => `- [ ] ${c}`).join("\n")}\n\n`
  + "**Definição de pronto:** código revisado, testes passando, documentação atualizada.";

export function openapi(titulo, recursos = ["itens"]) {
  const linhas = ["openapi: 3.0.3", "info:", `  title: ${titulo}`, "  version: 0.1.0", "paths:"];
  for (const r of recursos) {
    const n = idSeguro(r);
    linhas.push(`  /${n}:`, "    get:", `      summary: Lista ${n}`, "      responses:", "        '200': {description: Lista}", "    post:",
      `      summary: Cria em ${n}`, "      responses:", "        '201': {description: Criado}", "        '422': {description: Dados inválidos}",
      `  /${n}/{id}:`, "    parameters:", "      - {name: id, in: path, required: true, schema: {type: integer}}", "    get:", `      summary: Busca em ${n}`,
      "      responses:", "        '200': {description: Encontrado}", "        '404': {description: Não encontrado}", "    delete:", `      summary: Remove de ${n}`,
      "      responses:", "        '204': {description: Removido}");
  }
  return linhas.join("\n") + "\n";
}

const CI = {
  python: ["actions/setup-python@v5", "python-version: '3.11'", "pip install -e .[dev]", "pytest -q"],
  node: ["actions/setup-node@v4", "node-version: 20", "npm ci", "npm test"],
  go: ["actions/setup-go@v5", "go-version: '1.22'", "go mod download", "go test ./..."],
};
const ALIAS = { javascript: "node", js: "node", nodejs: "node", py: "python", golang: "go" };

export function workflowCi(linguagem = "python") {
  const chave = ALIAS[linguagem.toLowerCase()] || linguagem.toLowerCase();
  if (!CI[chave]) throw new Error(`linguagem sem modelo de CI: ${linguagem} (use python, node ou go)`);
  const [acao, versao, instalar, testar] = CI[chave];
  return `name: CI\non:\n  push: {branches: [main]}\n  pull_request:\njobs:\n  testes:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n`
    + `      - uses: ${acao}\n        with:\n          ${versao}\n      - run: ${instalar}\n      - run: ${testar}\n`;
}

export function dockerfile(linguagem = "python", porta = 8000) {
  const chave = ALIAS[linguagem.toLowerCase()] || linguagem.toLowerCase();
  if (chave === "python") {
    return `FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nRUN useradd --create-home app\n`
      + `USER app\nEXPOSE ${porta}\nCMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${porta}"]\n`;
  }
  if (chave === "node") return `FROM node:20-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci --omit=dev\nCOPY . .\nUSER node\nEXPOSE ${porta}\nCMD ["node", "index.js"]\n`;
  throw new Error(`linguagem sem modelo de Dockerfile: ${linguagem} (use python ou node)`);
}

export const editorconfig = () => "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\ntrim_trailing_whitespace = true\n"
  + "indent_style = space\nindent_size = 4\n\n[*.{js,ts,json,html,css,yml,yaml}]\nindent_size = 2\n";

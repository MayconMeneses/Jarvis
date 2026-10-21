// Gera movel/proxy/nvidia-worker.js (UM arquivo, para colar no editor da Cloudflare) a partir dos módulos de movel/proxy/fonte/.
// Uso: node movel/proxy/montar.mjs        (o teste worker.test.mjs confere que o arquivo gerado está em dia)
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const AQUI = fileURLToPath(new URL(".", import.meta.url));
const ORDEM = ["seguranca", "cors", "buscar", "limite", "texto", "rotas-novas", "nvidia", "agendado", "entrada"];
const CABECALHO = `// Proxy do Super Jarvis para Cloudflare Workers (plano grátis). ARQUIVO GERADO por movel/proxy/montar.mjs a partir de movel/proxy/fonte/*.js: não edite aqui.
// Rotas: /v1/... (NVIDIA), /brave/res/v1/... (Brave), GET /rss?url=, /ler?url=, /ical?url= (https público, só para a ORIGEM) e GET /saude (sem Origin).
// Não guarda chave nenhuma. Como reimplantar: docs/CELULAR-INDEPENDENTE.md.
`;

export function montar() {
  const partes = ORDEM.map((nome) => readFileSync(`${AQUI}fonte/${nome}.js`, "utf8").split(/\r?\n/)
    .filter((l) => !/^import .* from ".*";\s*$/.test(l) && l.trim() !== "" && !l.trim().startsWith("//"))
    .map((l) => l.replace(/^export (?!default)/, ""))
    .join("\n"));
  return CABECALHO + partes.join("\n") + "\n";
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  writeFileSync(`${AQUI}nvidia-worker.js`, montar());
  console.log("nvidia-worker.js gerado");
}

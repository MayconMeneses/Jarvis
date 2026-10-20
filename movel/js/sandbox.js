// Executa código num ambiente ISOLADO: um iframe sem acesso ao app (sandbox="allow-scripts", sem same-origin) com uma política de
// segurança própria, e dentro dele um Worker (outra thread: um laço infinito não trava a tela e é encerrado pelo tempo limite).
// O código rodado não enxerga a memória, as chaves nem o IndexedDB do app. JavaScript: sem rede nenhuma. Python (Pyodide): só
// consegue baixar o próprio Python do jsDelivr. Limite honesto: protege de acidentes; revise o código antes de rodar.
import { HARNESS_PY, trabalhadorJs, trabalhadorPy } from "./sandbox-codigo.js";

export const TEMPO_PADRAO = 10000, TEMPO_PYTHON = 60000;
const fonteDe = (fn) => `(${fn.toString()})()`;
export const FONTES = { javascript: fonteDe(trabalhadorJs), python: fonteDe(trabalhadorPy) };

export function resumir(linhas, ok, estourou, ms, erro = "") {
  const resumo = [...linhas].reverse().find((l) => /^\d+ passaram, \d+ falharam$/.test(l));
  const testes = resumo ? { passaram: +resumo.split(" ")[0], falharam: +resumo.split(" ")[2] } : null;
  const aprovado = estourou ? false : testes ? testes.falharam === 0 && testes.passaram > 0 : ok;
  const saida = linhas.join("\n") + (erro ? `\n[erro] ${erro}` : "") + (estourou ? "\n⏱ Interrompido: passou do tempo limite." : "");
  return { ok: aprovado, estourou, ms, saida: saida.trim(), testes, texto: `${saida.trim()}\n[${aprovado ? "terminou bem" : "falhou"}, ${(ms / 1000).toFixed(1)} s]`.trim() };
}

export function executar({ linguagem, arquivos, principal = "", modo = "rodar", tempoMs, documento = document }) {
  const python = linguagem === "python";
  const limite = tempoMs || (python ? TEMPO_PYTHON : TEMPO_PADRAO);
  return new Promise((resolver) => {
    const inicio = Date.now(), linhas = [];
    const iframe = documento.createElement("iframe");
    iframe.setAttribute("sandbox", "allow-scripts");  // sem allow-same-origin: origem opaca, sem acesso ao armazenamento do app
    iframe.style.cssText = "display:none;width:0;height:0;border:0";
    iframe.src = python ? "sandbox/py.html" : "sandbox/js.html";
    let fim = false, prontoTimer, tempoTimer;
    const encerrar = (ok, estourou, erro = "") => {
      if (fim) return;
      fim = true;
      clearTimeout(prontoTimer); clearTimeout(tempoTimer);
      window.removeEventListener("message", ouvir);
      iframe.remove();  // derruba o Worker junto
      resolver(resumir(linhas, ok, estourou, Date.now() - inicio, erro));
    };
    function ouvir(ev) {
      if (ev.source !== iframe.contentWindow) return;  // só ouve o próprio ambiente isolado
      const d = ev.data || {};
      if (d.tipo === "pronto") {
        clearTimeout(prontoTimer);
        iframe.contentWindow.postMessage({ fonte: FONTES[linguagem], entrada: { arquivos, principal, modo, harness: HARNESS_PY } }, "*");
        tempoTimer = setTimeout(() => encerrar(false, true), limite);
      } else if (d.tipo === "saida") linhas.push(String(d.linha).slice(0, 2000));
      else if (d.tipo === "fim") encerrar(Boolean(d.ok), false);
    }
    window.addEventListener("message", ouvir);
    prontoTimer = setTimeout(() => encerrar(false, false, "este navegador não conseguiu iniciar o ambiente isolado"), 8000);
    documento.body.appendChild(iframe);
  });
}

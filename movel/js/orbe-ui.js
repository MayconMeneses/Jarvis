// Liga o canvas #orbe (orbe de filamentos do HUD, que também aparece no modo foco) à página: tamanho com DPR, rótulo do estado,
// cores do tema ativo, pausa fora da tela, chave de movimento "orbe_modo" (lembrada no aparelho) e "reduzir movimento" do sistema.
import { OrbeFil, ROTULOS } from "./orbe-fil.js";
import { modoEfetivo } from "./orbe.js";
import { aplicarEfeitos, vigiarAba } from "./temas.js";

const $ = (id) => document.getElementById(id);
const css = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome);
const coresDoTema = () => ({ ciano: css("--ciano"), laranja: css("--laranja"), brilho: css("--brilho") });

export async function ligarOrbe(memoria) {
  const canvas = $("orbe");
  if (!canvas || !canvas.getContext || !canvas.getContext("2d")) return null;
  const orbe = new OrbeFil(canvas, { cores: coresDoTema });
  const reduzir = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const seletor = $("orbe-modo");
  seletor.value = (await memoria.meta("orbe_modo")) || "auto";
  const aplicar = () => { const modo = modoEfetivo(seletor.value, reduzir.matches); orbe.definirModo(modo); aplicarEfeitos(modo); };  // Efeitos: orbe e aurora juntos
  const medir = () => { const larg = canvas.clientWidth; if (larg) orbe.medir(larg, window.devicePixelRatio || 1); };
  const rotular = (estado) => {
    const palco = $("palco");
    if ($("orbe-rotulo")) $("orbe-rotulo").textContent = ROTULOS[estado];
    if ($("foco-rotulo")) $("foco-rotulo").textContent = ROTULOS[estado];
    if (palco) palco.dataset.estado = estado;
    document.documentElement.dataset.orbe = estado;
  };
  orbe.aoMudar(rotular);
  rotular(orbe.estadoAtual);
  seletor.addEventListener("change", () => { memoria.definirMeta("orbe_modo", seletor.value); aplicar(); });
  if (reduzir.addEventListener) reduzir.addEventListener("change", aplicar);
  let espera = 0;
  const remedir = () => { clearTimeout(espera); espera = setTimeout(medir, 120); };  // o buffer só é refeito quando o tamanho muda de verdade
  if (window.ResizeObserver) new ResizeObserver(remedir).observe(canvas); else window.addEventListener("resize", remedir);
  if (window.IntersectionObserver) new IntersectionObserver((e) => orbe.definirNaTela(e[e.length - 1].isIntersecting)).observe(canvas);
  if (window.MutationObserver) new MutationObserver(() => orbe.recolorir()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-tema"] });
  vigiarAba();
  aplicar();
  medir();
  orbe.iniciar();
  window.__orbeDebug = () => orbe.depurar();
  return orbe;
}

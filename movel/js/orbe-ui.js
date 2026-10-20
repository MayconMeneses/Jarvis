// Liga o canvas do cabeçalho ao Orbe: tamanho (com DPR), chave manual de movimento (lembrada no aparelho) e "reduzir movimento" do sistema.
import { Orbe, modoEfetivo } from "./orbe.js";
import { aplicarEfeitos, vigiarAba } from "./temas.js";

const $ = (id) => document.getElementById(id);

export async function ligarOrbe(memoria) {
  const canvas = $("orbe");
  if (!canvas || !canvas.getContext || !canvas.getContext("2d")) return null;
  const orbe = new Orbe(canvas);
  const reduzir = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const seletor = $("orbe-modo");
  seletor.value = (await memoria.meta("orbe_modo")) || "auto";
  const aplicar = () => { const modo = modoEfetivo(seletor.value, reduzir.matches); orbe.definirModo(modo); aplicarEfeitos(modo); };  // Efeitos: orbe e aurora juntos
  const medir = () => { const r = canvas.getBoundingClientRect(); if (r.width) orbe.redimensionar(r.width, r.height, window.devicePixelRatio || 1); };
  seletor.addEventListener("change", () => { memoria.definirMeta("orbe_modo", seletor.value); aplicar(); });
  if (reduzir.addEventListener) reduzir.addEventListener("change", aplicar);
  if (window.ResizeObserver) new ResizeObserver(medir).observe(canvas); else window.addEventListener("resize", medir);
  vigiarAba();
  aplicar();
  medir();
  orbe.iniciar();
  return orbe;
}

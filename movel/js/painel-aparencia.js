// Cérebro > Aparência: escolher o tema e os efeitos.
import { TEMAS, aplicarTema, guardarTema, lerTema } from "./temas.js";

const $ = (id) => document.getElementById(id);

export async function ligarAparencia(memoria) {
  $("tema-sel").replaceChildren(...TEMAS.map((t) => new Option(t.rotulo, t.id)));
  $("tema-sel").value = aplicarTema(await lerTema(memoria));
  $("tema-sel").addEventListener("change", async () => { $("tema-sel").value = aplicarTema($("tema-sel").value); await guardarTema(memoria, $("tema-sel").value); });
}

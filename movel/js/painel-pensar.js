// Cérebro > "Como pensar": escolhe automático, aprender ou só nuvem, e mostra quem está pensando (rótulo no foco e na conversa).
import { MODOS, NOTAS, ROTULOS } from "./pensar.js";

const $ = (id) => document.getElementById(id);

export function ligarPensar(pensador) {
  const seletor = $("como-pensar");
  seletor.replaceChildren(...MODOS.map((m) => Object.assign(document.createElement("option"), { value: m, textContent: ROTULOS[m] })));
  const nota = () => { seletor.value = pensador.modoAtual; $("como-pensar-nota").textContent = NOTAS[pensador.modoAtual]; };
  seletor.addEventListener("change", () => pensador.definirModo(seletor.value));
  const rotular = (texto) => { nota(); for (const id of ["foco-cerebro", "cerebro-ativo"]) { const el = $(id); if (el) el.textContent = texto; } };
  pensador.aoMudar(rotular);
  pensador.status().then(rotular);
}

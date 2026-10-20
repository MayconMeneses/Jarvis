// Seção do painel Cérebro: ligar "Aprender sozinha", ver o que aprendeu e avaliar o cérebro. Também liga o agendador de ociosidade.
import { Agendador } from "./agendador.js";

const $ = (id) => document.getElementById(id);

export function ligarAutonomo({ autonomo, avaliador, avisar, agendador = new Agendador({ tarefa: () => ciclo() }) }) {
  async function ciclo() {
    if (!(await autonomo.ligado())) return;
    const feito = await autonomo.ciclo();
    if (feito?.ok) { avisar(`Aprendi sozinha sobre "${feito.assunto}" (nota em Memória → Aprendizado).`); await atualizar(); }
    if (await avaliador.disponivel() && await avaliador.vencida()) { avisar(await avaliador.executar()); mostrarNota(); }
  }

  async function atualizar() {
    const feitos = (await autonomo.registro()).filter((r) => r.ok).slice(0, 8);
    $("auto-lista").replaceChildren(...(feitos.length ? feitos : [{ assunto: "nada ainda" }]).map((r) => {
      const li = document.createElement("li");
      li.textContent = r.quando ? `${r.assunto} (${r.origem})` : r.assunto;
      return li;
    }));
  }
  const mostrarNota = async () => { $("avaliacao-status").textContent = await avaliador.resumo(); };

  $("auto-ligado").addEventListener("change", async () => {
    await autonomo.definirLigado($("auto-ligado").checked);
    avisar($("auto-ligado").checked ? "Aprender sozinha ligada: vale com o app aberto e parado por 10 minutos." : "Aprender sozinha desligada.");
  });
  $("avaliar-agora").addEventListener("click", async () => {
    $("avaliar-agora").disabled = true;
    $("avaliacao-status").textContent = "Avaliando… (5 tarefas; pode levar alguns minutos)";
    try { $("avaliacao-status").textContent = await avaliador.executar(); } catch (e) { $("avaliacao-status").textContent = "Não consegui avaliar: " + e.message; }
    $("avaliar-agora").disabled = false;
  });
  // Qualquer toque ou tecla conta como uso: só estuda quando você largou o app aberto.
  for (const ev of ["pointerdown", "keydown", "touchstart"]) document.addEventListener(ev, () => agendador.atividade(), { passive: true });

  return async () => {
    $("auto-ligado").checked = await autonomo.ligado();
    await atualizar();
    await mostrarNota();
    agendador.iniciar();
  };
}

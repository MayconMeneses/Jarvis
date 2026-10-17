// Aba Cérebro: escolher o modelo, baixar e ligar (com aprovação explícita) ou desligar.
import { MODELOS, RECOMENDADO } from "./cerebro.js";

const $ = (id) => document.getElementById(id);

export function ligarCerebro(cerebro, memoria, avisar) {
  $("suporte").textContent = cerebro.suportado()
    ? "Este aparelho tem WebGPU: o cérebro de IA pode rodar aqui."
    : "Este navegador não tem WebGPU. No iPhone é preciso o iOS 26 ou mais novo (Safari). O motor de regras continua funcionando.";
  $("modelo").replaceChildren(...MODELOS.map((m) => {
    const op = document.createElement("option");
    op.value = m.id;
    op.textContent = `${m.rotulo} — ~${m.mb} MB`;
    return op;
  }));
  $("modelo").value = RECOMENDADO;
  const nota = () => { $("modelo-nota").textContent = MODELOS.find((m) => m.id === $("modelo").value)?.nota || ""; };
  $("modelo").addEventListener("change", nota);
  nota();

  const estado = (ligado) => { $("ligar").hidden = ligado; $("desligar").hidden = !ligado; $("modelo").disabled = ligado; };

  async function ligar(id) {
    $("progresso").hidden = false;
    $("ligar").disabled = true;
    try {
      await cerebro.carregar(id, (texto, p) => { $("cerebro-status").textContent = texto; $("progresso").value = p; });
      await memoria.definirMeta("cerebro", id);
      $("cerebro-status").textContent = "Cérebro de IA ligado. Converse na aba Conversa.";
      estado(true);
      avisar("Cérebro de IA ligado neste celular.");
    } catch (e) {
      $("cerebro-status").textContent = "Não consegui ligar: " + e.message;
    } finally {
      $("progresso").hidden = true;
      $("ligar").disabled = false;
    }
  }

  $("ligar").addEventListener("click", () => {
    const m = MODELOS.find((x) => x.id === $("modelo").value);
    if (confirm(`Baixar ${m.rotulo} (cerca de ${m.mb} MB) para este aparelho? Use Wi-Fi. O download acontece uma vez e o modelo fica guardado.`)) ligar(m.id);
  });
  $("desligar").addEventListener("click", async () => {
    await cerebro.descarregar();
    await memoria.definirMeta("cerebro", null);
    estado(false);
    $("cerebro-status").textContent = "Cérebro de IA desligado. O motor de regras continua.";
  });

  // Se já estava ligado da última vez, tenta religar sozinho (o modelo já está no aparelho, não baixa de novo).
  return async () => {
    const id = await memoria.meta("cerebro");
    if (id && cerebro.suportado()) await ligar(id);
  };
}

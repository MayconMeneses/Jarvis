// Aba Cérebro > Nuvem: cadastrar as suas chaves de API (Gemini, OpenAI, Groq, OpenRouter, outro/proxy), testar, remover e escolher a ordem.
import { PROVEDORES } from "./nuvem.js";

const $ = (id) => document.getElementById(id);

export function ligarNuvem(nuvem, memoria, avisar) {
  $("nv-provedor").replaceChildren(...Object.entries(PROVEDORES).map(([id, p]) => new Option(p.nome, id)));

  async function desenhar() {
    const p = PROVEDORES[$("nv-provedor").value];
    $("nv-dica").textContent = p.dica;
    $("nv-base-linha").hidden = !p.exigeBase;
    $("nv-modelo").placeholder = p.modelo || "nome do modelo";
    const salvas = await nuvem.salvas();
    $("nv-lista").replaceChildren(...salvas.map((s) => {
      const li = document.createElement("li");
      li.textContent = `${s.nome} — ${s.modelo} `;
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = "Remover";
      b.addEventListener("click", async () => { await nuvem.remover(s.id); desenhar(); });
      li.append(b);
      return li;
    }));
    $("nv-ordem-linha").hidden = !salvas.length;
  }

  $("nv-provedor").addEventListener("change", desenhar);
  $("nv-salvar").addEventListener("click", async () => {
    const id = $("nv-provedor").value;
    const p = PROVEDORES[id];
    if (!confirm(`As suas perguntas serão enviadas ao ${p.nome} quando eu usar a nuvem (o motor de regras e o cérebro do aparelho continuam sem enviar nada). Continuar?`)) return;
    $("nv-status").textContent = "Testando a chave…";
    $("nv-salvar").disabled = true;
    try {
      const modelo = await nuvem.salvar(id, $("nv-chave").value, { base: $("nv-base").value.trim(), modelo: $("nv-modelo").value.trim() });
      $("nv-chave").value = "";  // a chave não fica na tela
      $("nv-status").textContent = `${p.nome} guardado (modelo ${modelo}). A chave fica só neste aparelho e não entra na cópia de segurança.`;
      avisar(`${p.nome} cadastrado.`);
      await desenhar();
    } catch (e) {
      $("nv-status").textContent = "A chave não funcionou: " + e.message;
    } finally { $("nv-salvar").disabled = false; }
  });

  $("nv-ordem").addEventListener("change", () => memoria.definirMeta("nuvem_ordem", $("nv-ordem").value));
  return async () => { $("nv-ordem").value = (await memoria.meta("nuvem_ordem")) || "aparelho"; await desenhar(); };
}

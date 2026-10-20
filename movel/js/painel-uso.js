// Cérebro > Uso de IA: contadores por fonte, custo estimado, orçamento com alerta, gráfico dos últimos 30 dias, preços editáveis e cópia em JSON.
// Nunca mostra nem exporta chaves de API: só números.
import { FONTES, PRECOS_PADRAO } from "./uso.js";
import { desenharGrafico } from "./uso-grafico.js";

const $ = (id) => document.getElementById(id);
const usd = (v) => "US$ " + v.toFixed(2).replace(".", ",");

export function ligarUso({ uso, avisar }) {
  async function precos() {
    const cfg = await uso.config();
    $("uso-precos-campos").replaceChildren(...Object.keys(PRECOS_PADRAO).flatMap((id) => {
      const rotulo = document.createElement("label"), linha = document.createElement("div");
      rotulo.textContent = id === "referencia" ? "Referência (para o \"economizado\")" : FONTES[id];
      linha.className = "linha";
      for (const [campo, dica] of [["e", "US$/1M entrada"], ["s", "US$/1M saída"], ["c", "US$/chamada"]]) {
        const entrada = document.createElement("input");
        Object.assign(entrada, { type: "number", min: "0", step: "any", value: String(cfg.precos[id][campo]), ariaLabel: `${rotulo.textContent}: ${dica}` });
        entrada.placeholder = dica; entrada.dataset.fonte = id; entrada.dataset.campo = campo;
        linha.append(entrada);
      }
      return [rotulo, linha];
    }));
  }

  async function atualizar() {
    const r = await uso.resumo(), cfg = await uso.config();
    $("uso-lista").replaceChildren(...(r.fontes.length ? r.fontes : [{ nome: "Nenhuma chamada registrada neste mês", vazio: true }]).map((f) => {
      const li = document.createElement("li"), detalhe = document.createElement("small");
      li.append(f.nome);
      if (!f.vazio) detalhe.textContent = `${f.c} chamada(s)${f.id === "brave" ? "" : `, ${f.e + f.s} tokens${f.x ? " (alguns estimados)" : ""}`} — ${f.id === "aparelho" ? "custo zero" : usd(f.custo)}`;
      li.append(detalhe);
      return li;
    }));
    $("uso-total").textContent = `Gasto estimado no mês: ${usd(r.gasto)}.${r.economizado > 0 ? ` Economizado com o cérebro do aparelho: ${usd(r.economizado)}.` : ""} Preços de partida: confira nos sites dos provedores.`;
    $("uso-orcamento").value = cfg.orcamento || ""; $("uso-alerta").value = cfg.alerta;
    $("uso-barra").hidden = r.pct === null; $("uso-barra").value = Math.min(100, r.pct || 0);
    $("uso-alerta-msg").textContent = r.alerta ? `Atenção: você usou ${r.pct.toFixed(0)}% do orçamento do mês.` : r.pct !== null ? `Você usou ${r.pct.toFixed(0)}% do orçamento do mês.` : "";
    desenharGrafico($("uso-grafico"), await uso.serieDiaria(30));
    return r;
  }

  $("uso-salvar").addEventListener("click", async () => {
    const precosNovos = {};
    for (const i of $("uso-precos-campos").querySelectorAll("input")) (precosNovos[i.dataset.fonte] ||= {})[i.dataset.campo] = Math.max(0, Number(i.value) || 0);
    await uso.definirConfig({ orcamento: Math.max(0, Number($("uso-orcamento").value) || 0), alerta: Math.min(100, Math.max(1, Number($("uso-alerta").value) || 80)), precos: precosNovos });
    avisar("Orçamento e preços do Uso de IA salvos."); await atualizar();
  });
  $("uso-exportar").addEventListener("click", async () => {
    const blob = new Blob([await uso.exportar()], { type: "application/json" }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "jarvis-uso-ia.json"; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  });
  $("uso-importar").addEventListener("click", () => $("uso-arquivo").click());
  $("uso-arquivo").addEventListener("change", async () => {
    try { avisar(`Uso importado (${await uso.importar(await $("uso-arquivo").files[0].text())} registros).`); await precos(); await atualizar(); }
    catch (e) { avisar("Não consegui importar: " + e.message); }
    $("uso-arquivo").value = "";
  });
  $("painel-uso").addEventListener("toggle", async () => { if ($("painel-uso").open) { await precos(); await atualizar(); } });
  return atualizar;
}

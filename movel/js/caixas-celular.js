// Caixas do Início que vêm do próprio celular: "Uso de IA" (contadores do mês) e "Agentes" (o que roda dentro do app).
// Mesmo molde das outras caixas (criarCaixa). Só contadores e rótulos: nunca chaves nem textos de conversa. Tudo com textContent.
import { criarCaixa, el } from "./caixa-base.js";
import { contextoAgentes } from "./painel-agentes.js";

const usd = (v) => "US$ " + Number(v || 0).toFixed(2).replace(".", ",");

export function montarUso(container, ctx, { uso }) {
  return criarCaixa(container, ctx, {
    id: "uso-ia", titulo: "Uso de IA", ttlMs: 5 * 60000,
    async carregar() {
      const r = await uso.resumo();
      return r.fontes.length ? { dados: r } : { vazio: "Nenhum uso de IA neste mês." };
    },
    desenhar(r, corpo) {
      corpo.append(el("p", { className: "caixa-destaque", textContent: `${usd(r.gasto)} no mês` }));
      if (r.pct !== null) corpo.append(el("progress", { max: 100, value: Math.min(100, r.pct), "aria-label": "Uso do orçamento" }), el("p", { className: r.alerta ? "aviso" : "nota", textContent: `${r.pct.toFixed(0)}% do orçamento de ${usd(r.orcamento)}.` }));
      const lista = el("ul", { className: "caixa-lista sem-marca" });
      for (const f of r.fontes.slice(0, 5)) lista.append(el("li", {}, `${f.nome}: ${f.c} chamadas`, el("small", { className: "nota", textContent: f.custo ? ` ${usd(f.custo)}` : " sem custo" })));
      corpo.append(lista);
      if (r.economizado > 0) corpo.append(el("p", { className: "nota", textContent: `O cérebro do aparelho economizou cerca de ${usd(r.economizado)}.` }));
    },
  });
}

export function montarAgentes(container, ctx, { agentes, autonomo, avaliador, cerebro }) {
  return criarCaixa(container, ctx, {
    id: "agentes", titulo: "Agentes do app", ttlMs: 2 * 60000,
    async carregar() { return { dados: await agentes.todos(await contextoAgentes({ autonomo, avaliador, cerebro })) }; },
    desenhar(lista, corpo) {
      const ul = el("ul", { className: "caixa-lista sem-marca" });
      for (const a of lista) {
        const li = el("li", {}, el("span", { className: "estado-ag", textContent: a.rotulo }), a.nome, el("small", { className: "nota", textContent: `${a.quando}${a.situacao === "fechado" ? ". Só roda com o app aberto." : ""}` }));
        li.dataset.estado = a.situacao;
        ul.append(li);
      }
      corpo.append(ul);
    },
  });
}

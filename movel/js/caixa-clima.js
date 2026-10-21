// Caixa Clima (Open-Meteo direto, sem chave). A cidade fica na memória (a mesma do comando "clima em ...").
import { climaDados } from "./info.js";
import { criarCaixa, el } from "./caixa-base.js";

const SEM_CIDADE = 'Informe a sua cidade abaixo (ou diga "minha cidade é Fortaleza" na conversa).';

function desenhar(c, corpo) {
  corpo.append(
    el("p", { className: "caixa-destaque", textContent: `${c.agoraC}°C · ${c.condicao}` }),
    el("p", { textContent: `${c.local}. Sensação de ${c.sensacaoC}°C, máxima de ${c.maxC}°C e mínima de ${c.minC}°C.` }),
    el("p", { className: "nota", textContent: [c.chuvaPct != null ? `Chance de chuva: ${c.chuvaPct}%` : "", c.umidade != null ? `Umidade: ${c.umidade}%` : "", `Vento: ${c.ventoKmh} km/h`].filter(Boolean).join(" · ") }));
}

export function montar(container, ctx) {
  const extra = (recarregar) => {
    const campo = el("input", { type: "text", autocomplete: "off", placeholder: "Trocar de cidade", maxLength: 60, spellcheck: false });
    campo.setAttribute("aria-label", "Cidade do clima");
    const salvar = el("button", { type: "button", textContent: "Usar esta cidade" });
    salvar.addEventListener("click", async () => {
      const cidade = campo.value.replace(/\s+/g, " ").trim();
      if (!cidade) return;
      await ctx.memoria.definirMeta("cidade", cidade.toLowerCase());
      campo.value = "";
      recarregar();
    });
    return el("div", { className: "linha" }, campo, salvar);
  };
  return criarCaixa(container, ctx, {
    id: "clima", titulo: "Clima", extra,
    async carregar() {
      const cidade = await ctx.memoria.meta("cidade");
      if (!cidade) return { vazio: SEM_CIDADE };
      const c = await climaDados(cidade, ctx.buscar);
      if (!c) return { vazio: `Não achei a cidade "${cidade}". Tente outro nome abaixo.` };
      return { dados: c };
    },
    desenhar,
  });
}

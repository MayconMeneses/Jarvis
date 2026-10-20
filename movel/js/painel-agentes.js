// Cérebro > Agentes: lista o estado dos processos do app (tudo com textContent, nada de HTML montado de texto).
const $ = (id) => document.getElementById(id);

export function ligarAgentes({ agentes, autonomo, avaliador, cerebro }) {
  async function atualizar() {
    const historico = await avaliador.historico();
    const contexto = {
      ligados: { aprender: await autonomo.ligado(), avaliacao: (await autonomo.ligado()) && (await avaliador.disponivel()), cerebro: cerebro.ligado() },
      ultimos: { avaliacao: historico[0] ? Date.parse(historico[0].quando) : null },
    };
    $("ag-lista").replaceChildren(...(await agentes.todos(contexto)).map((a) => {
      const li = document.createElement("li"), estado = document.createElement("span"), detalhe = document.createElement("small");
      li.dataset.estado = a.situacao;
      estado.className = "estado-ag";
      estado.textContent = a.rotulo;
      detalhe.textContent = `${a.quando} — ${a.nota}${a.situacao === "fechado" ? ". Só roda com o app aberto." : ""}`;
      li.append(estado, a.nome, detalhe);
      return li;
    }));
  }
  $("ag-atualizar").addEventListener("click", atualizar);
  $("painel-agentes").addEventListener("toggle", () => { if ($("painel-agentes").open) atualizar(); });
  return atualizar;
}

  // ── Uso de IA: janela com totais, cota, orçamento, gráficos e tabelas (DOM com textContent) ──
  const usoDialog = document.getElementById("uso");
  const usoEl = (id) => document.getElementById(id);
  let usoDados = null, usoOrdem = { campo: "custo", dir: -1 };

  function usoNum(n) { return n >= 1e9 ? (n / 1e9).toFixed(2) + " G" : n >= 1e6 ? (n / 1e6).toFixed(2) + " M" : n >= 1e3 ? (n / 1e3).toFixed(1) + " k" : String(Math.round(n)); }
  function usoUsd(v) { return "US$ " + Number(v).toFixed(2); }
  function usoNo(tag, texto, cls) { const e = document.createElement(tag); if (texto != null) e.textContent = texto; if (cls) e.className = cls; return e; }
  function usoData(ts) { return new Date(ts * 1000).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); }
  function usoDizer(texto, ok) { const i = usoEl("uso-info"); i.textContent = texto || ""; i.className = "feedback " + (ok === false ? "on-no" : "on-ok"); }

  function usoKpis(t, locais, orc) {
    const itens = [["Respostas", usoNum(t.msgs)], ["Saída", usoNum(t.tout)], ["Cache", usoNum(t.cw + t.cr)],
      ["Valor equivalente", usoUsd(t.custo) + (t.estimado ? " ~" : "")], ["Sem IA", locais.pct_local.toFixed(0) + "%"]];
    if (orc.cotacao_brl) itens[3][1] += " (R$ " + (t.custo * orc.cotacao_brl).toFixed(2) + ")";
    usoEl("uso-kpis").replaceChildren(...itens.map(([k, v]) => { const d = usoNo("div"); d.append(usoNo("dt", k), usoNo("dd", v)); return d; }));
  }

  function usoMedidor(titulo, pct, alerta, linha, nota) {
    const box = usoNo("div", null, "uso-medidor" + (pct >= 95 ? " crit" : alerta ? " warn" : ""));
    const trilho = usoNo("div", null, "trilho"), barra = document.createElement("i");
    barra.style.width = Math.min(pct || 0, 100) + "%"; trilho.append(barra);
    box.append(usoNo("div", titulo + ": " + linha), trilho);
    if (nota) box.append(usoNo("small", nota, "uso-nota"));
    return box;
  }

  function usoJanela(titulo, m) {
    const linha = m.pct == null ? usoNum(m.usado) + " usados (sem teto: calibre abaixo)" : m.pct.toFixed(0) + "% do teto estimado";
    const nota = "Reset " + usoData(m.fim) + (m.msgs ? " · " + m.msgs + " respostas" : "") + (m.acaba_antes_do_reset ? " · nesse ritmo a cota acaba antes do reset" : "");
    return usoMedidor(titulo, m.pct, m.alerta, linha, nota);
  }

  function usoOrcamento(o) {
    if (!o.orcamento) return usoNo("p", "Gasto no mês " + usoUsd(o.gasto) + " · projeção " + usoUsd(o.projecao) + ". Defina um orçamento em \"Teto, orçamento e preços\" para receber alerta.", "uso-nota");
    return usoMedidor("Orçamento", o.pct, o.alerta, o.pct.toFixed(0) + "% usado", usoUsd(o.gasto) + " de " + usoUsd(o.orcamento) + " · projeção " + usoUsd(o.projecao) + (o.projecao_estoura ? " (acima do orçamento)" : ""));
  }

  function usoTabela(tabela, colunas, linhas, ordenavel) {
    const cab = document.createElement("tr");
    colunas.forEach(([campo, nome]) => {
      const th = document.createElement("th");
      if (ordenavel) {
        const b = usoNo("button", nome + (usoOrdem.campo === campo ? (usoOrdem.dir < 0 ? " ▼" : " ▲") : ""));
        b.type = "button";
        b.addEventListener("click", () => { usoOrdem = { campo, dir: usoOrdem.campo === campo ? -usoOrdem.dir : -1 }; usoDesenhar(); });
        th.append(b);
      } else th.textContent = nome;
      cab.append(th);
    });
    tabela.tHead.replaceChildren(cab);
    const ordenadas = ordenavel ? [...linhas].sort((a, b) => (a[usoOrdem.campo] > b[usoOrdem.campo] ? 1 : -1) * usoOrdem.dir) : linhas;
    tabela.tBodies[0].replaceChildren(...ordenadas.map((l) => {
      const tr = document.createElement("tr");
      colunas.forEach(([campo]) => {
        const td = usoNo("td", campo === "custo" ? (l.preco_ok ? usoUsd(l.custo) : "sem preço") : typeof l[campo] === "number" ? usoNum(l[campo]) : l[campo]);
        if (campo === "custo" && !l.preco_ok) td.className = "sem-preco";
        tr.append(td);
      });
      return tr;
    }));
  }

  function usoOpcoes(id, valores, atual) {
    const sel = usoEl(id);
    sel.replaceChildren(new Option("todos", ""), ...valores.map((v) => new Option(v, v)));
    sel.value = atual || "";
  }

  function usoDesenhar() {
    const d = usoDados;
    usoEl("uso-vazio").hidden = !d.vazio;
    usoEl("uso-corpo").hidden = d.vazio;
    usoOpcoes("uso-f-modelo", d.opcoes.modelos, d.filtros.modelo);
    usoOpcoes("uso-f-projeto", d.opcoes.projetos, d.filtros.projeto);
    usoPreencherConfig(d.config);
    if (d.vazio) return;
    usoKpis(d.totais, d.locais, d.orcamento);
    const avisos = [];
    if (d.sem_preco.length) avisos.push("Modelo sem preço: " + d.sem_preco.join(", ") + " (custo parcial).");
    if (d.totais.estimado) avisos.push("Valores em dólar são equivalentes em API pela tabela de preços (a assinatura não cobra por token).");
    usoEl("uso-aviso").textContent = avisos.join(" ");
    usoEl("uso-cota").replaceChildren(usoJanela("Janela de 5 h" + (d.cota.janela_5h.ativa ? "" : " (nenhuma aberta)"), d.cota.janela_5h), usoJanela("Semana", d.cota.semana), usoNo("p", d.cota.aviso, "uso-nota"));
    usoEl("uso-orc").replaceChildren(usoOrcamento(d.orcamento));
    UsoGraficos.barras(usoEl("uso-dias"), d.por_dia);
    const fatias = d.por_modelo.filter((m) => m.custo > 0 || m.tout > 0).map((m) => ({ nome: m.nome, valor: m.custo > 0 ? m.custo : m.tout / 1e6 }));
    UsoGraficos.rosca(usoEl("uso-rosca"), fatias);
    usoEl("uso-legenda").replaceChildren(...fatias.map((f, i) => {
      const li = document.createElement("li"), c = document.createElement("i");
      c.style.background = UsoGraficos.cor(i);
      li.append(c, document.createTextNode(f.nome));
      return li;
    }));
    usoTabela(usoEl("uso-tabela"), [["nome", "Modelo"], ["msgs", "Resp."], ["tin", "Entrada"], ["tout", "Saída"], ["cw", "Cache esc."], ["cr", "Cache leit."], ["custo", "US$ equiv."]], d.por_modelo, true);
    usoTabela(usoEl("uso-tabela2"), [["nome", "Projeto"], ["msgs", "Resp."], ["tout", "Saída"], ["custo", "US$ equiv."]], d.por_projeto, false);
  }

  async function usoCarregar() {
    const filtros = { modelo: usoEl("uso-f-modelo").value, projeto: usoEl("uso-f-projeto").value, sub: usoEl("uso-f-sub").value };
    const d = await window.pywebview.api.uso_resumo(usoEl("uso-periodo").value, filtros);
    if (d.error) { usoDizer(d.error, false); return; }
    usoDados = d;
    usoDesenhar();
  }

  usoEl("open-uso").addEventListener("click", () => { usoDialog.showModal(); usoCarregar(); });
  usoEl("close-uso").addEventListener("click", () => usoDialog.close());
  usoEl("uso-atualizar").addEventListener("click", usoCarregar);
  for (const id of ["uso-periodo", "uso-f-modelo", "uso-f-projeto", "uso-f-sub"]) usoEl(id).addEventListener("change", usoCarregar);
  window.addEventListener("resize", () => { if (usoDialog.open && usoDados && !usoDados.vazio) usoDesenhar(); });

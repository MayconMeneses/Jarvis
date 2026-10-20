  // ── Uso de IA: teto/orçamento/câmbio, tabela de preços, calibração, exportar e importar ──
  const USO_CAMPOS = [["plano", "Plano (rótulo)", "text"], ["teto_5h", "Teto da janela de 5 h", "number"], ["teto_semana", "Teto semanal", "number"],
    ["orcamento_mensal", "Orçamento mensal (US$)", "number"], ["alerta_pct", "Alertar a partir de (%)", "number"], ["cotacao_brl", "Cotação R$ por US$", "number"],
    ["peso_cr", "Peso da leitura de cache (0 a 1)", "number"]];
  let usoPrecos = { modelos: {} };

  function usoCampoConfig(campo, rotulo, tipo) {
    const label = document.createElement("label"), input = document.createElement("input");
    input.id = "uso-c-" + campo; input.type = tipo; if (tipo === "number") input.step = "any";
    label.append(document.createTextNode(rotulo), input);
    return label;
  }

  function usoPreencherConfig(cfg) {
    const caixa = usoEl("uso-cfg");
    if (!caixa.children.length) {
      caixa.replaceChildren(...USO_CAMPOS.map((c) => usoCampoConfig(...c)));
      const sel = document.createElement("label"), s = document.createElement("select");
      s.id = "uso-c-unidade"; s.append(new Option("tokens ponderados", "tokens"), new Option("mensagens", "mensagens"));
      sel.append(document.createTextNode("Unidade da cota"), s); caixa.append(sel);
    }
    for (const [campo] of USO_CAMPOS) usoEl("uso-c-" + campo).value = cfg[campo] == null ? "" : cfg[campo];
    usoEl("uso-c-unidade").value = cfg.unidade;
  }

  function usoLinhaPreco(modelo, p) {
    const tr = document.createElement("tr");
    const nome = document.createElement("input"); nome.value = modelo; nome.setAttribute("aria-label", "Modelo");
    const celulas = [nome, ...["in", "out"].map((k) => { const i = document.createElement("input"); i.type = "number"; i.step = "any"; i.min = "0"; i.setAttribute("aria-label", k === "in" ? "Preço de entrada" : "Preço de saída"); i.value = p[k] == null ? "" : p[k]; i.placeholder = "sem preço"; return i; })];
    celulas.forEach((c) => { const td = document.createElement("td"); td.append(c); tr.append(td); });
    return tr;
  }

  async function usoCarregarPrecos() {
    usoPrecos = await window.pywebview.api.uso_precos();
    usoEl("uso-precos").tBodies[0].replaceChildren(...Object.entries(usoPrecos.modelos).map(([m, p]) => usoLinhaPreco(m, p)));
  }

  usoEl("uso-preco-novo").addEventListener("click", () => usoEl("uso-precos").tBodies[0].append(usoLinhaPreco("", {})));

  usoEl("uso-salvar").addEventListener("click", async () => {
    const cfg = { unidade: usoEl("uso-c-unidade").value };
    for (const [campo] of USO_CAMPOS) cfg[campo] = usoEl("uso-c-" + campo).value;
    const modelos = {};
    for (const tr of usoEl("uso-precos").tBodies[0].rows) {
      const [m, i, o] = [...tr.querySelectorAll("input")].map((x) => x.value);
      if (m.trim()) modelos[m.trim()] = { in: i, out: o };
    }
    await window.pywebview.api.uso_salvar_config(cfg);
    await window.pywebview.api.uso_salvar_precos({ ...usoPrecos, modelos });
    usoDizer("Configuração e preços salvos.", true);
    await usoCarregar();
    await usoCarregarPrecos();
  });

  async function usoCalibrar(pct) {
    const res = await window.pywebview.api.uso_calibrar(usoEl("uso-cal-janela").value, pct);
    usoDizer(res.error || "Teto ajustado para " + usoNum(res.teto) + ".", !res.error);
    if (!res.error) usoCarregar();
  }
  usoEl("uso-cal").addEventListener("click", () => usoCalibrar(Number(usoEl("uso-cal-pct").value)));
  usoEl("uso-limite").addEventListener("click", () => usoCalibrar(100));

  async function usoMover(metodo, arg) {
    const res = await window.pywebview.api[metodo](arg);
    if (res.cancelado) return;
    usoDizer(res.error || res.text, !res.error);
    if (metodo === "uso_importar" && !res.error) usoCarregar();
  }
  usoEl("uso-exp-json").addEventListener("click", () => usoMover("uso_exportar", "json"));
  usoEl("uso-exp-csv").addEventListener("click", () => usoMover("uso_exportar", "csv"));
  usoEl("uso-imp").addEventListener("click", () => usoMover("uso_importar"));
  usoEl("open-uso").addEventListener("click", usoCarregarPrecos);

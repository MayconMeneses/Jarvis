  // ── Radar de Notícias ─────────────────────────────────────────
  const radarDialog = document.getElementById("radar");
  const radarInfo = document.getElementById("radar-info");
  const radarFontes = document.getElementById("radar-fontes");
  const radarCampos = { nicho: "radar-nicho", hora: "radar-hora" };
  const radarSwitches = { ativo: "radar-ativo", dias_uteis: "radar-uteis", usar_ia: "radar-ia", audio: "radar-audio" };

  function radarSay(text, ok) {
    radarInfo.textContent = text || "";
    radarInfo.className = "feedback " + (ok ? "on-ok" : "on-no");
  }

  async function radarRefresh() {
    const s = await window.pywebview.api.radar_estado();
    for (const [chave, id] of Object.entries(radarCampos)) document.getElementById(id).value = s[chave];
    for (const [chave, id] of Object.entries(radarSwitches)) document.getElementById(id).checked = s[chave];
    document.getElementById("radar-ia").disabled = !s.ia_disponivel;
    radarFontes.replaceChildren(...s.fontes.map((f) => {
      const li = document.createElement("li");
      const label = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox"; box.checked = f.ativa;
      box.addEventListener("change", () => window.pywebview.api.radar_fonte_ativar(f.nome, box.checked));
      const small = document.createElement("small");
      small.textContent = ` ${f.tipo} · ${f.idioma} · nota ${f.nota}${f.medida ? "" : " (palpite)"}`;
      label.append(box, " " + f.nome, small);
      li.append(label);
      return li;
    }));
    const u = s.ultima;
    radarSay((s.rodando ? "Rodando agora… " : "") + (u ? `Última: ${u.dia}, ${u.escolhidos} itens de ${u.varridos} (${u.resultado}).` : "Ainda não rodou."), true);
  }

  async function radarSalvar() {
    const campos = {};
    for (const [chave, id] of Object.entries(radarCampos)) campos[chave] = document.getElementById(id).value;
    for (const [chave, id] of Object.entries(radarSwitches)) campos[chave] = document.getElementById(id).checked;
    const res = await window.pywebview.api.radar_salvar(campos);
    radarSay(res.error || "Configuração salva.", !res.error);
    await radarRefresh();
  }

  document.getElementById("open-radar").addEventListener("click", async () => { radarDialog.showModal(); await radarRefresh(); });
  document.getElementById("close-radar").addEventListener("click", () => radarDialog.close());
  document.getElementById("radar-salvar").addEventListener("click", radarSalvar);
  for (const [id, metodo, args] of [["radar-gerar", "radar_rodar", [false]], ["radar-texto", "radar_rodar", [true]],
                                    ["radar-ouvir", "radar_ouvir", []], ["radar-parar", "radar_parar", []], ["radar-abrir", "radar_abrir", []]]) {
    document.getElementById(id).addEventListener("click", async () => {
      const res = await window.pywebview.api[metodo](...args);
      radarSay(res.error || res.text, !res.error);
    });
  }
  document.getElementById("radar-add").addEventListener("click", async () => {
    const campo = document.getElementById("radar-url");
    if (!campo.value.trim()) return;
    radarSay("Procurando o feed e conferindo a fonte…", true);
    const res = await window.pywebview.api.radar_fonte_adicionar(campo.value);
    campo.value = "";
    await radarRefresh();
    radarSay(res.text, !res.text.startsWith("Não adicionei"));
  });

  // ── painel de cérebros ───────────────────────────────────────
  const brainsDialog = document.getElementById("brains");

  function setStatus(id, on, yes, no) {
    const el = document.getElementById(id);
    el.textContent = on ? yes : no;
    el.className = on ? "on-ok" : "on-no";
  }

  async function refreshBrains() {
    let s;
    try { s = await window.pywebview.api.brains_status(); } catch (e) { return false; }
    setStatus("st-claude", s.claude, "● conectado", "● não encontrado");
    setStatus("st-gemini", s.gemini, "● chave ok", "● sem chave");
    setStatus("st-nvidia", s.nvidia, "● chave ok", "● sem chave");
    setStatus("st-brave", s.brave, "● chave ok", "● opcional");
    document.querySelectorAll('input[name="uso"]').forEach((r) => { r.checked = r.value === s.uso_gemini; });
    document.getElementById("standalone").checked = !!s.somente_independente;
    document.getElementById("autonomo-on").checked = !!s.autonomo;
    document.getElementById("llm-local").checked = !!s.llm_local;
    document.getElementById("voz-online").checked = !!s.voz_online;
    setStatus("st-llm", s.llm_pronto, "● instalado", "● não instalado");
    refreshModelos();
    return true;
  }

  async function refreshModelos() {
    const sel = document.getElementById("llm-modelo");
    let lista = [];
    try { lista = await window.pywebview.api.llm_modelos(); } catch (e) { return; }
    sel.replaceChildren();
    lista.forEach((m) => {
      const o = document.createElement("option");
      o.value = m.id;
      o.textContent = m.nome + (m.instalado ? "" : " (não instalado)") + (m.recomendado ? " ★" : "");
      o.title = m.aviso;
      sel.appendChild(o);
    });
    const ativo = lista.find((m) => m.ativo);
    if (ativo) sel.value = ativo.id;
    const mostrar = () => { const m = lista.find((x) => x.id === sel.value); document.getElementById("info-llm-modelo").textContent = m ? m.descricao + " " + m.aviso : ""; };
    sel.onchange = async () => {
      mostrar();
      const res = await window.pywebview.api.set_llm_modelo(sel.value);
      const fb = document.getElementById("fb-llm-modelo");
      fb.textContent = res.mensagem;
      fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
      if (!res.ok && ativo) sel.value = ativo.id;
    };
    mostrar();
  }

  document.getElementById("llm-voltar").addEventListener("click", async () => {
    const res = await window.pywebview.api.llm_voltar_antigo();
    const fb = document.getElementById("fb-llm-modelo");
    fb.textContent = res.mensagem;
    fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
    refreshModelos();
  });

  document.getElementById("autonomo-on").addEventListener("change", async (ev) => {
    const res = await window.pywebview.api.set_autonomo(ev.target.checked);
    const fb = document.getElementById("fb-autonomo");
    fb.textContent = res.mensagem;
    fb.className = "feedback on-ok";
  });

  document.getElementById("voz-online").addEventListener("change", async (ev) => {
    const res = await window.pywebview.api.set_voz_online(ev.target.checked);
    const fb = document.getElementById("fb-voz");
    fb.textContent = res.mensagem;
    fb.className = "feedback on-ok";
  });

  document.getElementById("llm-local").addEventListener("change", async (ev) => {
    const res = await window.pywebview.api.set_llm(ev.target.checked);
    const fb = document.getElementById("fb-llm");
    fb.textContent = res.mensagem;
    fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
    ev.target.checked = !!res.ligado;
  });

  document.getElementById("standalone").addEventListener("change", async (ev) => {
    const res = await window.pywebview.api.set_standalone(ev.target.checked);
    const fb = document.getElementById("fb-standalone");
    fb.textContent = res.mensagem;
    fb.className = "feedback on-ok";
  });

  document.getElementById("open-brains").addEventListener("click", async () => {
    brainsDialog.showModal();
    if (!(await refreshBrains())) { const fb = document.getElementById("fb-tema"); fb.textContent = "Não consegui ler o estado dos cérebros agora. Feche e abra de novo."; fb.className = "feedback on-no"; }
  });
  document.getElementById("close-brains").addEventListener("click", () => brainsDialog.close());

  brainsDialog.querySelectorAll("[data-save]").forEach((btn) => btn.addEventListener("click", async () => {
    const provider = btn.dataset.save;
    const field = document.getElementById("key-" + provider);
    const fb = document.getElementById("fb-" + provider);
    if (!field.value.trim()) { fb.textContent = "Cole a chave primeiro."; field.focus(); return; }
    btn.disabled = true;
    fb.className = "feedback";
    fb.textContent = "Testando a chave…";
    let res;
    try {
      res = await window.pywebview.api.save_key(provider, field.value);
    } catch (err) {
      res = { ok: false, mensagem: "Falha ao falar com o núcleo da Jarvis: " + err };
    }
    btn.disabled = false;
    fb.textContent = res.mensagem;
    fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
    if (res.ok) field.value = "";  // a chave não fica na tela
    refreshBrains();
  }));

  brainsDialog.querySelectorAll("[data-remove]").forEach((btn) => btn.addEventListener("click", async () => {
    await window.pywebview.api.remove_key(btn.dataset.remove);
    document.getElementById("fb-" + btn.dataset.remove).textContent = "Chave removida.";
    refreshBrains();
  }));

  brainsDialog.querySelectorAll("[data-link]").forEach((btn) => btn.addEventListener("click",
    () => window.pywebview.api.open_link(btn.dataset.link)));

  document.querySelectorAll('input[name="uso"]').forEach((r) => r.addEventListener("change",
    () => window.pywebview.api.set_gemini_mode(r.value)));

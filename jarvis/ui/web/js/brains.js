  // ── painel de cérebros ───────────────────────────────────────
  const brainsDialog = document.getElementById("brains");

  function setStatus(id, on, yes, no) {
    const el = document.getElementById(id);
    el.textContent = on ? yes : no;
    el.className = on ? "on-ok" : "on-no";
  }

  async function refreshBrains() {
    const s = await window.pywebview.api.brains_status();
    setStatus("st-claude", s.claude, "● conectado", "● não encontrado");
    setStatus("st-gemini", s.gemini, "● chave ok", "● sem chave");
    setStatus("st-nvidia", s.nvidia, "● chave ok", "● sem chave");
    setStatus("st-brave", s.brave, "● chave ok", "● opcional");
    document.querySelectorAll('input[name="uso"]').forEach((r) => { r.checked = r.value === s.uso_gemini; });
    document.getElementById("standalone").checked = !!s.somente_independente;
  }

  document.getElementById("standalone").addEventListener("change", async (ev) => {
    const res = await window.pywebview.api.set_standalone(ev.target.checked);
    const fb = document.getElementById("fb-standalone");
    fb.textContent = res.mensagem;
    fb.className = "feedback on-ok";
  });

  document.getElementById("open-brains").addEventListener("click", async () => {
    await refreshBrains();
    brainsDialog.showModal();
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

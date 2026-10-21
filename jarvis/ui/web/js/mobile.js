  // ── Jarvis no celular ────────────────────────────────────────
  // Aviso de rede enviado pelo PC (campo opcional: pode não existir). Texto puro, curto e discreto.
  function mostrarAviso(texto) {
    const el = document.getElementById("mobile-aviso"), t = typeof texto === "string" ? texto.replace(/\s+/g, " ").trim().slice(0, 300) : "";
    el.textContent = t; el.hidden = !t;
  }
  async function refreshMobile() {
    let s;
    try { s = await window.pywebview.api.mobile_status(); } catch (e) { return; }
    document.getElementById("mobile-on").checked = s.ligado;
    document.getElementById("mobile-url").textContent = s.ligado ? s.url : "";
    mostrarAviso(s.aviso_rede);
    document.getElementById("mobile-devices").replaceChildren();
    s.aparelhos.forEach((a) => {
      const li = document.createElement("li");
      li.textContent = a.nome + " ";
      const b = document.createElement("button");
      b.type = "button"; b.className = "ghost"; b.textContent = "Remover";
      b.addEventListener("click", async () => { await window.pywebview.api.mobile_revoke(a.id); refreshMobile(); });
      li.appendChild(b);
      document.getElementById("mobile-devices").appendChild(li);
    });
  }
  document.getElementById("mobile-on").addEventListener("change", async (ev) => {
    const res = await window.pywebview.api.mobile_set(ev.target.checked);
    const fb = document.getElementById("fb-mobile");
    fb.textContent = res.mensagem; fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
    mostrarAviso(res.aviso_rede);
    refreshMobile();
  });
  document.getElementById("mobile-code").addEventListener("click", async () => {
    const res = await window.pywebview.api.mobile_code();
    const fb = document.getElementById("fb-mobile");
    fb.textContent = res.ok ? "Código: " + res.codigo + " — " + res.mensagem : res.mensagem;
    fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
  });
  document.getElementById("open-brains").addEventListener("click", refreshMobile);

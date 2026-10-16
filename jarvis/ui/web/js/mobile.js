  // ── Jarvis no celular ────────────────────────────────────────
  async function refreshMobile() {
    const s = await window.pywebview.api.mobile_status();
    document.getElementById("mobile-on").checked = s.ligado;
    document.getElementById("mobile-url").textContent = s.ligado ? s.url : "";
    document.getElementById("mobile-devices").innerHTML = "";
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
    refreshMobile();
  });
  document.getElementById("mobile-code").addEventListener("click", async () => {
    const res = await window.pywebview.api.mobile_code();
    const fb = document.getElementById("fb-mobile");
    fb.textContent = res.ok ? "Código: " + res.codigo + " — " + res.mensagem : res.mensagem;
    fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
  });
  document.getElementById("open-brains").addEventListener("click", refreshMobile);

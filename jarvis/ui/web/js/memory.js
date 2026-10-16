  // ── memória da Jarvis ─────────────────────────────────────────
  const memDialog = document.getElementById("memory");
  const memList = document.getElementById("mem-list");
  const memText = document.getElementById("mem-text");
  const memInfo = document.getElementById("mem-info");
  const memSave = document.getElementById("mem-save");
  const memDelete = document.getElementById("mem-delete");
  let memRef = null;

  function memSay(text, ok) {
    memInfo.textContent = text || "";
    memInfo.className = "feedback " + (ok ? "on-ok" : "on-no");
  }

  function memSelect(ref) {
    memRef = ref;
    memText.hidden = memSave.hidden = memDelete.hidden = !ref;
    memList.querySelectorAll("button").forEach((b) => b.setAttribute("aria-current", String(b.dataset.ref === ref)));
  }

  async function memRefresh() {
    const res = await window.pywebview.api.memory_list(document.getElementById("mem-search").value);
    if (res.error) { memSay(res.error, false); return; }
    memList.replaceChildren(...res.notas.map((n) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.ref = n.ref;
      b.append(n.ref);
      if (n.resumo || n.atualizado) {
        const s = document.createElement("small");
        s.textContent = [n.atualizado, n.resumo].filter(Boolean).join(" · ");
        b.append(s);
      }
      b.addEventListener("click", async () => {
        const note = await window.pywebview.api.memory_get(n.ref);
        if (note.error) { memSay(note.error, false); return; }
        memText.value = note.texto;
        memSelect(n.ref);
        memSay("");
      });
      li.append(b);
      return li;
    }));
    memSelect(res.notas.some((n) => n.ref === memRef) ? memRef : null);
    if (!memRef) memText.value = "";
    memSay(res.total + " nota(s) na memória.", true);
  }

  document.getElementById("open-memory").addEventListener("click", async () => {
    memDialog.showModal();
    await memRefresh();
  });
  document.getElementById("close-memory").addEventListener("click", () => memDialog.close());
  let memTimer = null;
  document.getElementById("mem-search").addEventListener("input", () => {
    clearTimeout(memTimer);
    memTimer = setTimeout(memRefresh, 250);
  });
  memSave.addEventListener("click", async () => {
    const res = await window.pywebview.api.memory_save(memRef, memText.value);
    memSay(res.error || "Nota salva.", !res.error);
    if (!res.error) memRefresh();
  });
  memDelete.addEventListener("click", async () => {
    if (!confirm("Apagar esta nota da memória da Jarvis?\n\n" + memRef)) return;
    const res = await window.pywebview.api.memory_delete(memRef);
    memRef = null;
    await memRefresh();
    memSay(res.error || "Nota apagada.", !res.error);
  });
  document.getElementById("mem-export").addEventListener("click", async () => {
    const res = await window.pywebview.api.memory_export();
    if (res.cancelado) return;
    memSay(res.error || res.text, !res.error);
  });

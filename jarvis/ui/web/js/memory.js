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

  const MEM_SEM_PONTE = "Não consegui falar com a Jarvis agora. Feche e abra a Memória de novo.";

  async function memOpen(ref) {
    let note;
    try { note = await window.pywebview.api.memory_get(ref); } catch (e) { memSay(MEM_SEM_PONTE, false); return; }
    if (note.error) { memSay(note.error, false); return; }
    memText.value = note.texto;
    memSelect(ref);
    memSay("");
  }

  // Abas Lista / Mapa: o mapa carrega os dados só quando aberto e para de desenhar quando fechado.
  async function memAba(mapa) {
    memDialog.classList.toggle("mapa", mapa);
    document.getElementById("mem-mapa").hidden = !mapa;
    document.getElementById("mem-aba-mapa").setAttribute("aria-selected", String(mapa));
    document.getElementById("mem-aba-lista").setAttribute("aria-selected", String(!mapa));
    document.getElementById("mem-aba-mapa").tabIndex = mapa ? 0 : -1;
    document.getElementById("mem-aba-lista").tabIndex = mapa ? -1 : 0;
    if (!mapa) { MemoriaGrafo.parar(); return; }
    memSay("Montando o mapa…", true);
    let erro = "";
    try { erro = await MemoriaGrafo.mostrar(); } catch (e) { erro = MEM_SEM_PONTE; }
    memSay(erro || "", !erro);
  }
  MemoriaGrafo.aoAbrir(async (ref) => { await memAba(false); await memOpen(ref); });
  document.getElementById("mem-aba-lista").addEventListener("click", () => memAba(false));
  document.getElementById("mem-aba-mapa").addEventListener("click", () => memAba(true));
  // Abas: setas, Home e End movem entre Lista e Mapa (padrão de abas do WAI-ARIA); só a aba atual entra no Tab.
  document.querySelector(".mem-abas").addEventListener("keydown", (ev) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(ev.key)) return;
    ev.preventDefault();
    const mapa = ev.key === "ArrowRight" || ev.key === "End";
    document.getElementById(mapa ? "mem-aba-mapa" : "mem-aba-lista").focus();
    memAba(mapa);
  });
  memDialog.addEventListener("close", () => MemoriaGrafo.parar());

  async function memRefresh() {
    const busca = document.getElementById("mem-search").value.trim(), vazio = document.getElementById("mem-vazio");
    let res;
    try { res = await window.pywebview.api.memory_list(busca); } catch (e) { memSay(MEM_SEM_PONTE, false); return; }
    if (res.error) { memSay(res.error, false); return; }
    vazio.hidden = res.notas.length > 0;
    vazio.textContent = busca ? "Nenhuma nota encontrada para esta busca." : "Nada guardado ainda. O que a Jarvis aprender com você aparece aqui, para você revisar.";
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
      b.addEventListener("click", () => memOpen(n.ref));
      li.append(b);
      return li;
    }));
    memSelect(res.notas.some((n) => n.ref === memRef) ? memRef : null);
    if (!memRef) memText.value = "";
    memSay(res.total + " nota(s) na memória.", true);
  }

  document.getElementById("open-memory").addEventListener("click", async () => {
    memDialog.showModal();
    memSay("Carregando…", true);
    await memRefresh();
  });
  document.getElementById("close-memory").addEventListener("click", () => memDialog.close());
  let memTimer = null;
  document.getElementById("mem-search").addEventListener("input", () => {
    clearTimeout(memTimer);
    memTimer = setTimeout(memRefresh, 250);
  });
  memSave.addEventListener("click", async () => {
    let res;
    try { res = await window.pywebview.api.memory_save(memRef, memText.value); } catch (e) { memSay("Não consegui salvar agora. O texto continua aqui; tente de novo.", false); return; }
    memSay(res.error || "Nota salva.", !res.error);
    if (!res.error) memRefresh();
  });
  memDelete.addEventListener("click", async () => {
    if (!confirm("Apagar esta nota da memória da Jarvis?\n\n" + memRef)) return;
    let res;
    try { res = await window.pywebview.api.memory_delete(memRef); } catch (e) { memSay("Não consegui apagar agora. A nota continua guardada.", false); return; }
    memRef = null;
    await memRefresh();
    memSay(res.error || "Nota apagada.", !res.error);
  });
  for (const [id, metodo] of [["mem-backup", "memory_backup"], ["mem-restore", "memory_restore"]]) {
    document.getElementById(id).addEventListener("click", async () => {
      const campo = document.getElementById("mem-senha");
      let res;
      try { res = await window.pywebview.api[metodo](campo.value); } catch (e) { campo.value = ""; memSay("Não consegui fazer a cópia agora. Tente de novo.", false); return; }
      campo.value = "";  // a senha não fica na tela
      if (res.cancelado) return;
      memSay(res.error || res.text, !res.error);
      if (!res.error) memRefresh();
    });
  }
  document.getElementById("mem-export").addEventListener("click", async () => {
    let res;
    try { res = await window.pywebview.api.memory_export(); } catch (e) { memSay("Não consegui exportar agora. Tente de novo.", false); return; }
    if (res.cancelado) return;
    memSay(res.error || res.text, !res.error);
  });

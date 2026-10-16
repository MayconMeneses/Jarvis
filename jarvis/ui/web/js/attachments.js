  // ── anexos ───────────────────────────────────────────────────
  let pending = [];
  const chips = document.getElementById("chips");

  function renderChips() {
    chips.textContent = "";
    pending.forEach((f, i) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      const name = document.createElement("span");
      name.textContent = f.nome;
      name.title = f.nome;
      const info = document.createElement("small");
      info.textContent = `${f.tipo} · ${f.tamanho_kb} KB`;
      const remove = document.createElement("button");
      remove.type = "button"; remove.textContent = "×";
      remove.setAttribute("aria-label", "Remover " + f.nome);
      remove.addEventListener("click", () => { pending.splice(i, 1); renderChips(); });
      chip.append(name, info, remove);
      chips.appendChild(chip);
    });
  }

  function addAttachments(res) {
    pending.push(...(res.anexos || []));
    renderChips();
    (res.erros || []).forEach((e) => addError(e));
    input.focus();
  }

  document.getElementById("attach").addEventListener("click", async () => {
    addAttachments(await window.pywebview.api.pick_files());
  });

  const MAX_MB = 25;
  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }
  let dragDepth = 0;
  window.addEventListener("dragenter", (e) => { e.preventDefault(); dragDepth++; document.body.classList.add("dragging"); });
  window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; document.body.classList.remove("dragging"); } });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    dragDepth = 0;
    document.body.classList.remove("dragging");
    for (const file of e.dataTransfer?.files || []) {
      if (file.size > MAX_MB * 1024 * 1024) { addError(`'${file.name}' passa do limite de ${MAX_MB} MB`); continue; }
      addAttachments(await window.pywebview.api.attach_data(file.name, await readAsBase64(file)));
    }
  });

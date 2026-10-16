  function add(kind, text, meta) {
    hideSuggestions();
    const el = document.createElement("div");
    el.className = "msg " + kind;
    renderText(el, text);
    const m = document.createElement("span");
    m.className = "meta";
    m.textContent = meta ? `${now()} · ${meta}` : now();
    el.appendChild(m);
    log.appendChild(el);
    scrollDown();
    return el;
  }

  function addTyping() {
    const el = document.createElement("div");
    el.className = "msg jarvis";
    el.setAttribute("aria-label", "A Jarvis está pensando");
    el.innerHTML = '<span class="typing" aria-hidden="true"><i></i><i></i><i></i></span>';  // marcação fixa, sem dados
    log.appendChild(el);
    scrollDown();
    return el;
  }

  // Mensagem técnica do roteador → explicação curta, com os detalhes recolhidos.
  function friendlyError(raw) {
    const limit = raw.match(/session limit[^)]*resets ([^;(]+)/i) || raw.match(/limite de uso/i);
    if (limit) {
      const when = limit[1] ? ` (renova às ${limit[1].trim().replace(/\s*\(.*$/, "")})` : "";
      return ["O limite de uso do Claude acabou por enquanto" + when + ".",
              "Para continuar sem esperar, configure a chave grátis do Gemini ou da NVIDIA (veja o README)."];
    }
    if (/sem conexão|connection|getaddrinfo/i.test(raw)) return ["Sem conexão com a internet.", "Confira a rede e tente de novo."];
    return ["Não consegui responder agora.", ""];
  }

  function addError(raw, retryText, retryFiles = []) {
    hideSuggestions();
    const [title, hint] = friendlyError(String(raw));
    const el = document.createElement("div");
    el.className = "msg error";
    el.setAttribute("role", "alert");
    const t = document.createElement("div");
    t.className = "err-title";
    t.textContent = title;
    el.appendChild(t);
    if (hint) el.appendChild(document.createTextNode(hint));
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Detalhes técnicos";
    details.append(summary, document.createTextNode(String(raw)));
    el.appendChild(details);
    if (retryText || retryFiles.length) {
      const retry = document.createElement("button");
      retry.type = "button"; retry.className = "retry"; retry.textContent = "Tentar de novo";
      retry.addEventListener("click", () => { el.remove(); ask(retryText, false, retryFiles); });
      el.appendChild(retry);
    }
    log.appendChild(el);
    scrollDown();
  }

  function showSuggestions() {
    const box = document.createElement("div");
    box.className = "suggestions";
    box.id = "suggestions";
    SUGGESTIONS.forEach((text) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = text;
      b.addEventListener("click", () => ask(text, true));
      box.appendChild(b);
    });
    log.appendChild(box);
    scrollDown();
  }

  function hideSuggestions() { document.getElementById("suggestions")?.remove(); }

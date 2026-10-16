  // Só **negrito** e links http(s); o texto entra como nós de texto, nunca como HTML.
  // Links abrem no navegador padrão (pelo Python), não dentro da janela.
  function renderText(el, text) {
    text.split(/(\*\*[^*]+\*\*|https?:\/\/[^\s<>"')\]]+)/g).forEach((part) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) {
        const b = document.createElement("strong");
        b.textContent = part.slice(2, -2);
        el.appendChild(b);
      } else if (/^https?:\/\//.test(part)) {
        const a = document.createElement("a");
        a.href = "#";
        a.textContent = part.length > 60 ? part.slice(0, 57) + "…" : part;
        a.title = part;
        a.addEventListener("click", (e) => { e.preventDefault(); window.pywebview.api.open_link(part); });
        el.appendChild(a);
      } else if (part) {
        el.appendChild(document.createTextNode(part));
      }
    });
  }

// Markdown mínimo e SEGURO: monta nós do DOM (nunca innerHTML), então nada vindo da internet ou de um modelo vira código na página.
const INLINE = /(\*\*[^*]+\*\*|`[^`]+`)/g;

function inline(pai, texto) {
  for (const parte of texto.split(INLINE)) {
    if (!parte) continue;
    let no;
    if (parte.startsWith("**") && parte.endsWith("**") && parte.length > 4) { no = document.createElement("strong"); no.textContent = parte.slice(2, -2); }
    else if (parte.startsWith("`") && parte.endsWith("`") && parte.length > 2) { no = document.createElement("code"); no.textContent = parte.slice(1, -1); }
    else no = document.createTextNode(parte);
    pai.appendChild(no);
  }
}

function bloco(pai, texto) {
  let lista = null;
  for (const linha of texto.split("\n")) {
    const item = /^\s*[-*]\s+(.*)$/.exec(linha);
    if (item) {
      if (!lista) { lista = document.createElement("ul"); pai.appendChild(lista); }
      const li = document.createElement("li");
      inline(li, item[1]);
      lista.appendChild(li);
      continue;
    }
    lista = null;
    if (!linha.trim()) { pai.appendChild(document.createElement("br")); continue; }
    const p = document.createElement("p");
    inline(p, linha);
    pai.appendChild(p);
  }
}

export function renderizar(texto, pai = document.createDocumentFragment()) {
  texto.split(/```[\w+#-]*\n?/).forEach((trecho, i) => {
    if (i % 2) {
      const pre = document.createElement("pre"), code = document.createElement("code");
      code.textContent = trecho.replace(/\n$/, "");
      pre.appendChild(code);
      pai.appendChild(pre);
    } else if (trecho.trim()) bloco(pai, trecho);
  });
  return pai;
}

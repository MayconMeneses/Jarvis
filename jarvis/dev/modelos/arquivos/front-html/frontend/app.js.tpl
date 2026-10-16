// __NOME__: tela de exemplo (HTML + JavaScript puro). Fala com a API em API_URL.
const API_URL = window.API_URL || "http://localhost:8000";
const lista = document.getElementById("lista");
const aviso = document.getElementById("aviso");

async function chamar(caminho, opcoes = {}) {
  const resposta = await fetch(API_URL + caminho, {
    headers: { "content-type": "application/json" },
    ...opcoes,
  });
  if (!resposta.ok) throw new Error(`Falha ${resposta.status}`);
  return resposta.status === 204 ? null : resposta.json();
}

function desenhar(itens) {
  lista.replaceChildren(...itens.map((item) => {
    const li = document.createElement("li");
    li.className = item.concluido ? "feito" : "";
    const marca = document.createElement("input");
    marca.type = "checkbox";
    marca.checked = item.concluido;
    marca.setAttribute("aria-label", `Concluir: ${item.titulo}`);
    marca.addEventListener("change", () => agir(() => chamar(`/api/itens/${item.id}`, { method: "PATCH", body: JSON.stringify({ concluido: marca.checked }) })));
    const texto = document.createElement("span");
    texto.textContent = item.titulo;  // textContent: nunca interpreta HTML vindo da API
    const apagar = document.createElement("button");
    apagar.type = "button";
    apagar.textContent = "Apagar";
    apagar.addEventListener("click", () => agir(() => chamar(`/api/itens/${item.id}`, { method: "DELETE" })));
    li.append(marca, texto, apagar);
    return li;
  }));
}

async function carregar() {
  desenhar(await chamar("/api/itens"));
}

async function agir(acao) {
  aviso.textContent = "";
  try {
    await acao();
    await carregar();
  } catch (erro) {
    aviso.textContent = "Não consegui falar com a API. Ela está rodando em " + API_URL + "?";
  }
}

document.getElementById("formulario").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const campo = document.getElementById("titulo");
  const titulo = campo.value.trim();
  if (!titulo) return;
  agir(() => chamar("/api/itens", { method: "POST", body: JSON.stringify({ titulo }) })).then(() => { campo.value = ""; });
});

agir(() => Promise.resolve());

import { useEffect, useState } from "react";

// __NOME__: tela de exemplo (React). A API fica em VITE_API_URL (padrão http://localhost:8000).
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function chamar(caminho, opcoes = {}) {
  const resposta = await fetch(API_URL + caminho, { headers: { "content-type": "application/json" }, ...opcoes });
  if (!resposta.ok) throw new Error(`Falha ${resposta.status}`);
  return resposta.status === 204 ? null : resposta.json();
}

export default function App() {
  const [itens, setItens] = useState([]);
  const [titulo, setTitulo] = useState("");
  const [erro, setErro] = useState("");

  async function recarregar() {
    setItens(await chamar("/api/itens"));
  }

  async function agir(acao) {
    setErro("");
    try {
      await acao();
      await recarregar();
    } catch {
      setErro(`Não consegui falar com a API. Ela está rodando em ${API_URL}?`);
    }
  }

  useEffect(() => {
    agir(() => Promise.resolve());
  }, []);

  function adicionar(evento) {
    evento.preventDefault();
    const texto = titulo.trim();
    if (!texto) return;
    agir(() => chamar("/api/itens", { method: "POST", body: JSON.stringify({ titulo: texto }) })).then(() => setTitulo(""));
  }

  return (
    <main>
      <h1>__NOME__</h1>
      <form onSubmit={adicionar}>
        <label htmlFor="titulo" className="sr-only">Nova tarefa</label>
        <input id="titulo" value={titulo} onChange={(e) => setTitulo(e.target.value)}
               placeholder="O que precisa ser feito?" maxLength={200} required autoFocus />
        <button type="submit">Adicionar</button>
      </form>
      <p role="status" className="erro">{erro}</p>
      <ul aria-label="Tarefas">
        {itens.map((item) => (
          <li key={item.id} className={item.concluido ? "feito" : ""}>
            <input type="checkbox" checked={item.concluido} aria-label={`Concluir: ${item.titulo}`}
                   onChange={(e) => agir(() => chamar(`/api/itens/${item.id}`, { method: "PATCH", body: JSON.stringify({ concluido: e.target.checked }) }))} />
            <span>{item.titulo}</span>
            <button type="button" onClick={() => agir(() => chamar(`/api/itens/${item.id}`, { method: "DELETE" }))}>Apagar</button>
          </li>
        ))}
      </ul>
    </main>
  );
}

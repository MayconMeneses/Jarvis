// Aba Memória: ver, buscar, editar, apagar, salvar e restaurar a cópia de segurança. Tudo só neste aparelho.
import { cifrar, decifrar, eCifrado } from "./cripto.js";
import { ligarGrafo } from "./painel-grafo.js";

const $ = (id) => document.getElementById(id);

export function ligarMemoria(memoria, avisar) {
  let aberta = null;

  async function listar() {
    const consulta = $("busca").value.trim();
    const notas = consulta ? await memoria.buscar(consulta, 30) : (await memoria.listar()).slice(0, 60);
    $("notas").replaceChildren(...notas.map((n) => {
      const li = document.createElement("li");
      const titulo = document.createElement("b"), resumo = document.createElement("small");
      titulo.textContent = n.ref;
      resumo.textContent = n.corpo.replace(/\n/g, " ").slice(0, 120);
      li.append(titulo, resumo);
      li.tabIndex = 0;
      li.addEventListener("click", () => abrir(n));
      li.addEventListener("keydown", (e) => { if (e.key === "Enter") abrir(n); });
      return li;
    }));
    if (!notas.length) { const li = document.createElement("li"); li.textContent = "Nenhuma nota ainda. Diga \"lembre que ...\" na conversa."; $("notas").append(li); }
  }

  function abrir(nota) {
    aberta = nota;
    $("nota-ref").value = nota?.ref || "";
    $("nota-corpo").value = nota?.corpo || "";
    $("editor").hidden = false;
    $("nota-ref").focus();
  }

  // Notas (lista) ou Grafo (Second Brain em Canvas): tocar num nó abre a nota no mesmo editor.
  const grafo = ligarGrafo({ memoria, aoAbrirNota: (nota) => { abrir(nota); $("editor").scrollIntoView({ block: "nearest" }); } });
  const ver = (grafoAtivo) => {
    $("ver-notas").setAttribute("aria-pressed", String(!grafoAtivo));
    $("ver-grafo").setAttribute("aria-pressed", String(grafoAtivo));
    $("busca").hidden = $("notas").hidden = grafoAtivo;
    $("grafo-painel").hidden = !grafoAtivo;
    if (grafoAtivo) grafo.mostrar().catch((e) => avisar("Não consegui montar o grafo: " + e.message)); else { grafo.ocultar(); listar(); }
  };
  $("ver-notas").addEventListener("click", () => ver(false));
  $("ver-grafo").addEventListener("click", () => ver(true));
  $("busca").addEventListener("input", listar);
  $("nova-nota").addEventListener("click", () => abrir(null));
  $("nota-fechar").addEventListener("click", () => { $("editor").hidden = true; });
  $("nota-salvar").addEventListener("click", async () => {
    try {
      if (aberta && aberta.ref !== $("nota-ref").value.trim()) await memoria.apagar(aberta.ref);
      await memoria.guardar($("nota-ref").value, $("nota-corpo").value, aberta?.tipo || "nota");
      $("editor").hidden = true;
      await listar();
    } catch (e) { avisar(e.message); }
  });
  $("nota-apagar").addEventListener("click", async () => {
    if (aberta && confirm(`Apagar a nota "${aberta.ref}"?`)) { await memoria.apagar(aberta.ref); $("editor").hidden = true; await listar(); }
  });
  $("exportar").addEventListener("click", async () => {
    try {
      const arquivo = await cifrar(await memoria.exportar(), $("senha-copia").value);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob([arquivo], { type: "application/json" }));
      link.download = `jarvis-copia-${new Date().toLocaleDateString("sv")}.jarvis-backup`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 5000);
      avisar("Cópia segura gerada. Guarde a senha: sem ela a cópia não abre.");
    } catch (e) { avisar("Não consegui gerar a cópia: " + e.message); }
    $("senha-copia").value = "";
  });
  $("importar").addEventListener("click", () => $("arquivo").click());
  $("arquivo").addEventListener("change", async (ev) => {
    const arquivo = ev.target.files[0];
    if (!arquivo) return;
    try {
      const conteudo = await arquivo.text();
      avisar(`Restaurei ${await memoria.importar(eCifrado(conteudo) ? await decifrar(conteudo, $("senha-copia").value) : conteudo)} notas.`);
      await listar();
    } catch (e) { avisar("Não consegui restaurar: " + e.message); }
    $("senha-copia").value = "";
    ev.target.value = "";
  });
  return () => { if ($("grafo-painel").hidden) return listar(); return grafo.mostrar(); };
}

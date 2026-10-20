// Aba Oficina: projetos, arquivos, editor, rodar e testar (no sandbox), desfazer e baixar o ZIP. Tudo só neste aparelho.
// O que está nos arquivos (inclusive o que a IA escreveu) é dado: só executa quando você toca em Rodar ou Testar, e sempre isolado.
import { arquivosDoModelo, listarModelos } from "./modelos.js";
import { caminhoSeguro, EspacoOficina } from "./oficina-espaco.js";
import { executar } from "./sandbox.js";
import { zip } from "./zip.js";

const $ = (id) => document.getElementById(id);
const VAZIO = "";

export const linguagemDe = (caminho) => (/\.py$/i.test(caminho) ? "python" : /\.js$/i.test(caminho) ? "javascript" : "");

// Dá o arquivo ao usuário: um link temporário com download (no Safari do iPhone abre o menu de salvar em Arquivos).
export function baixar(nome, bytes, tipo = "application/zip") {
  const url = URL.createObjectURL(new Blob([bytes], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export function ligarOficina({ memoria, carregarModelos, avisar, aoRodar = null }) {
  const espaco = new EspacoOficina(memoria);
  let projeto = "", arquivos = {}, aberto = "", avisouPython = false;

  function saida(texto, estado = "") { $("of-saida").textContent = texto; $("of-saida").className = estado; }
  const erro = (e) => saida(e.message || String(e), "falhou");

  function desenharLista() {
    $("of-arquivos").replaceChildren(...Object.keys(arquivos).sort().map((caminho) => {
      const li = document.createElement("li"), b = document.createElement("button");
      b.type = "button";
      b.textContent = caminho;
      b.setAttribute("aria-current", String(caminho === aberto));
      b.addEventListener("click", () => selecionar(caminho));
      li.append(b);
      return li;
    }));
  }

  function selecionar(caminho) {
    aberto = caminho;
    $("of-nome").value = caminho;
    $("of-editor").value = arquivos[caminho] ?? VAZIO;
    desenharLista();
  }

  async function carregarProjetos(escolher) {
    const nomes = await espaco.projetos();
    $("of-projeto").replaceChildren(...(nomes.length ? nomes : ["(nenhum projeto ainda)"]).map((n) => new Option(n, nomes.length ? n : "")));
    if (escolher && nomes.includes(escolher)) $("of-projeto").value = escolher;
    projeto = $("of-projeto").value;
    await abrirProjeto();
  }

  async function abrirProjeto() {
    projeto = $("of-projeto").value;
    arquivos = projeto ? await espaco.arquivos(projeto) : {};
    const primeiro = Object.keys(arquivos).find((c) => linguagemDe(c) && !/test/i.test(c)) || Object.keys(arquivos).sort()[0] || "";
    aberto = "";
    if (primeiro) selecionar(primeiro); else { $("of-nome").value = ""; $("of-editor").value = VAZIO; desenharLista(); }
    saida("");
  }

  async function salvar() {
    if (!projeto) throw new Error("Crie um projeto primeiro (botão Novo projeto).");
    const nome = caminhoSeguro($("of-nome").value);
    await espaco.salvar(projeto, nome, $("of-editor").value);
    arquivos[nome] = $("of-editor").value;
    aberto = nome;
    $("of-nome").value = nome;
    desenharLista();
    return nome;
  }

  async function rodar(modo) {
    try {
      const nome = await salvar();
      const linguagem = modo === "testar" ? (linguagemDe(nome) || (Object.keys(arquivos).some((c) => c.endsWith(".py")) ? "python" : "javascript")) : linguagemDe(nome);
      if (!linguagem) throw new Error("Aqui rodam arquivos .js (JavaScript) e .py (Python). Escolha um deles.");
      if (linguagem === "python" && !avisouPython) {
        if (!confirm("O Python roda no navegador e é baixado do jsDelivr na primeira vez (cerca de 10 MB; use Wi-Fi). Continuar?")) return;
        avisouPython = true;
      }
      saida(modo === "testar" ? "Testando no ambiente isolado…" : "Rodando no ambiente isolado…");
      ["of-rodar", "of-testar"].forEach((id) => { $(id).disabled = true; });
      const r = await executar({ linguagem, arquivos: { ...arquivos }, principal: nome, modo });
      aoRodar?.("ok");
      saida(r.texto || "(sem saída)", r.ok ? "ok" : "falhou");
    } catch (e) { aoRodar?.("erro"); erro(e); } finally { ["of-rodar", "of-testar"].forEach((id) => { $(id).disabled = false; }); }
  }

  async function criarProjeto() {
    try {
      const nome = $("of-novo-nome").value.trim(), id = $("of-modelo").value;
      if ((await espaco.projetos()).includes(nome)) throw new Error("Já existe um projeto com esse nome.");
      await espaco.criar(nome);
      if (id) {
        const prontos = arquivosDoModelo(await carregarModelos(), id, nome, $("of-novo-desc").value);
        for (const [caminho, texto] of Object.entries(prontos)) await espaco.salvar(nome, caminho, texto);
      }
      $("of-form").hidden = true;
      await carregarProjetos(nome);
      avisar(`Projeto "${nome}" criado na Oficina.`);
    } catch (e) { erro(e); $("of-form").hidden = false; }
  }

  async function aoAbrir() {
    const modelos = await carregarModelos().catch(() => ({}));
    $("of-modelo").replaceChildren(new Option("Projeto vazio", ""), ...listarModelos(modelos).map((m) => new Option(`Modelo: ${m.descricao}`, m.id)));
    await carregarProjetos(projeto);
  }

  $("of-projeto").addEventListener("change", () => abrirProjeto().catch(erro));
  $("of-novo").addEventListener("click", () => { $("of-form").hidden = false; $("of-novo-nome").focus(); });
  $("of-cancelar").addEventListener("click", () => { $("of-form").hidden = true; });
  $("of-criar").addEventListener("click", criarProjeto);
  $("of-novo-arquivo").addEventListener("click", () => { aberto = ""; $("of-nome").value = "novo.py"; $("of-editor").value = VAZIO; desenharLista(); $("of-nome").focus(); });
  $("of-salvar").addEventListener("click", () => salvar().then((n) => saida(`Salvo: ${n}`, "ok")).catch(erro));
  $("of-desfazer").addEventListener("click", async () => {
    try {
      const nome = caminhoSeguro($("of-nome").value);
      arquivos[nome] = await espaco.desfazer(projeto, nome);
      selecionar(nome);
      saida(`Voltei a versão anterior de ${nome}. Toque em Desfazer de novo para refazer.`, "ok");
    } catch (e) { erro(e); }
  });
  $("of-apagar").addEventListener("click", async () => {
    try {
      const nome = caminhoSeguro($("of-nome").value);
      if (!confirm(`Apagar ${nome}? A versão anterior fica guardada para desfazer.`)) return;
      await espaco.apagar(projeto, nome);
      delete arquivos[nome];
      await abrirProjeto();
      saida(`${nome} apagado.`, "ok");
    } catch (e) { erro(e); }
  });
  $("of-rodar").addEventListener("click", () => rodar("rodar"));
  $("of-testar").addEventListener("click", () => rodar("testar"));
  $("of-zip").addEventListener("click", async () => {
    try {
      if (!projeto) throw new Error("Escolha um projeto.");
      const todos = await espaco.arquivos(projeto);
      if (!Object.keys(todos).length) throw new Error("O projeto ainda não tem arquivos.");
      baixar(`${projeto.replace(/\s+/g, "-")}.zip`, zip(todos));
      saida(`ZIP com ${Object.keys(todos).length} arquivos preparado. Salve em Arquivos.`, "ok");
    } catch (e) { erro(e); }
  });

  return { aoAbrir, espaco, escolher: (nome) => carregarProjetos(nome) };
}

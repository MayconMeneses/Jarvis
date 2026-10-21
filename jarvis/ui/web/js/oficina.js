  // ── Oficina (IDE): editar, rodar, testar e criar com IA ───────────────
  const ofDialog = document.getElementById("oficina");
  const ofProjeto = document.getElementById("of-projeto");
  const ofLista = document.getElementById("of-arquivos");
  const ofNome = document.getElementById("of-nome");
  const ofEditor = document.getElementById("of-editor");
  const ofSaida = document.getElementById("of-saida");
  const ofAviso = document.getElementById("of-aviso");
  let ofArquivos = {};

  function ofSay(texto, estado) {
    ofSaida.textContent = texto || "";
    ofSaida.className = estado || "";
  }

  function ofDesenharLista() {
    ofLista.replaceChildren(...Object.keys(ofArquivos).sort().map((caminho) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = caminho;
      b.setAttribute("aria-current", String(caminho === ofNome.value));
      b.addEventListener("click", () => { ofNome.value = caminho; ofEditor.value = ofArquivos[caminho]; ofDesenharLista(); });
      li.append(b);
      return li;
    }));
  }

  const OF_SEM_PONTE = "Não consegui falar com a Jarvis agora. Feche e abra a Oficina de novo.";

  async function ofCarregarProjetos(escolher) {
    let res;
    try { res = await window.pywebview.api.of_projetos(); } catch (e) { ofSay(OF_SEM_PONTE, "falhou"); return; }
    ofProjeto.replaceChildren(...res.projetos.map((p) => new Option(p, p)));
    if (escolher) ofProjeto.value = escolher;
    ofAviso.textContent = (res.python ? "" : "Python não encontrado neste PC. ") + (res.node ? "" : "Node.js não encontrado (JavaScript indisponível). ")
      + "Rodar e testar acontecem em um processo separado, com 10 s e 512 MB; revise o código antes de rodar.";
    if (ofProjeto.value) await ofAbrir();
  }

  async function ofAbrir() {
    let res;
    try { res = await window.pywebview.api.of_abrir(ofProjeto.value); } catch (e) { ofSay(OF_SEM_PONTE, "falhou"); return; }
    if (res.error) { ofSay(res.error, "falhou"); return; }
    ofArquivos = res.arquivos;
    const primeiro = Object.keys(ofArquivos).sort()[0] || "";
    ofNome.value = primeiro;
    ofEditor.value = primeiro ? ofArquivos[primeiro] : "";
    ofDesenharLista();
    ofSay("");
  }

  async function ofSalvar() {
    if (!ofProjeto.value) { ofSay("Crie um projeto primeiro.", "falhou"); return false; }
    let res;
    try { res = await window.pywebview.api.of_salvar(ofProjeto.value, ofNome.value, ofEditor.value); } catch (e) { ofSay("Não consegui salvar agora. O texto continua no editor.", "falhou"); return false; }
    if (res.error) { ofSay(res.error, "falhou"); return false; }
    ofArquivos[res.caminho] = ofEditor.value;
    ofNome.value = res.caminho;
    ofDesenharLista();
    return true;
  }

  async function ofExecutar(metodo, ...args) {
    if (!(await ofSalvar())) return;
    ofSay("Rodando no sandbox…");
    try {
      const res = await window.pywebview.api[metodo](ofProjeto.value, ...args);
      ofSay(res.error || res.texto, res.error || !res.ok ? "falhou" : "ok");
    } catch (e) { ofSay("Não consegui rodar agora. Tente de novo em instantes.", "falhou"); }
  }

  document.getElementById("open-oficina").addEventListener("click", async () => { ofDialog.showModal(); await ofCarregarProjetos(); });
  document.getElementById("close-oficina").addEventListener("click", () => ofDialog.close());
  ofProjeto.addEventListener("change", ofAbrir);
  document.getElementById("of-novo-projeto").addEventListener("click", async () => {
    const nome = prompt("Nome do novo projeto (letras, números, espaço e hífen):");
    if (!nome) return;
    const res = await window.pywebview.api.of_criar_projeto(nome);
    if (res.error) { ofSay(res.error, "falhou"); return; }
    await ofCarregarProjetos(nome.trim());
  });
  document.getElementById("of-novo-arquivo").addEventListener("click", () => { ofNome.value = "novo.py"; ofEditor.value = ""; ofNome.focus(); });
  document.getElementById("of-salvar").addEventListener("click", async () => { if (await ofSalvar()) ofSay("Salvo.", "ok"); });
  document.getElementById("of-rodar").addEventListener("click", () => ofExecutar("of_rodar", ofNome.value));
  document.getElementById("of-testar").addEventListener("click", () => ofExecutar("of_testar", ofNome.value.endsWith(".js") ? "javascript" : "python"));
  document.getElementById("of-desfazer").addEventListener("click", async () => {
    const res = await window.pywebview.api.of_desfazer(ofProjeto.value, ofNome.value);
    if (res.error) { ofSay(res.error, "falhou"); return; }
    ofEditor.value = ofArquivos[ofNome.value] = res.conteudo;
    ofSay("Voltei para a versão anterior (desfazer de novo refaz).", "ok");
  });
  document.getElementById("of-apagar").addEventListener("click", async () => {
    if (!ofNome.value || !confirm("Apagar " + ofNome.value + "? A versão anterior fica no histórico.")) return;
    await window.pywebview.api.of_apagar(ofProjeto.value, ofNome.value);
    await ofAbrir();
  });
  ofEditor.addEventListener("keydown", (ev) => {  // Tab insere 4 espaços em vez de sair do editor
    if (ev.key !== "Tab") return;
    ev.preventDefault();
    const { selectionStart: a, selectionEnd: b } = ofEditor;
    ofEditor.setRangeText("    ", a, b, "end");
  });

  document.getElementById("of-ia").addEventListener("click", async () => {
    const descricao = document.getElementById("of-descricao").value.trim();
    if (!ofProjeto.value) { ofSay("Crie um projeto primeiro (botão Novo projeto).", "falhou"); return; }
    if (descricao.length < 10) { ofSay("Descreva o que criar (pelo menos uma frase).", "falhou"); return; }
    if (!confirm("A Jarvis vai escrever os arquivos deste projeto com IA e rodar os testes que ela mesma criou, no sandbox. Continuar?")) return;
    const botaoIa = document.getElementById("of-ia");
    botaoIa.disabled = true;  // uma criação por vez
    try { await ofCriarComIa(descricao); } catch (e) { ofSay("Perdi o contato com a Jarvis durante a criação. Confira os arquivos do projeto.", "falhou"); }
    botaoIa.disabled = false;
  });

  async function ofCriarComIa(descricao) {
    const inicio = await window.pywebview.api.of_criar_ia(ofProjeto.value, descricao);
    if (inicio.error) { ofSay(inicio.error, "falhou"); return; }
    for (let voltas = 0; voltas < 900; voltas++) {  // no máximo ~30 min
      await new Promise((r) => setTimeout(r, 2000));
      const est = await window.pywebview.api.of_estado_ia();
      if (est.rodando) { ofSay("✨ " + (est.status || "criando…")); continue; }
      if (est.erro) { ofSay("Não consegui criar: " + est.erro, "falhou"); return; }
      const r = est.resultado;
      await ofAbrir();
      if (r.principal) { ofNome.value = r.principal; ofEditor.value = ofArquivos[r.principal] || ""; ofDesenharLista(); }
      ofSay(["Criei " + r.arquivos.length + " arquivo(s): " + r.arquivos.join(", ") + ".", r.testes ? "\nTestes (rodados no sandbox):\n" + r.testes : "\nSem testes para rodar.",
        r.avisos.length ? "\nAtenção: " + r.avisos.join("; ") : ""].join("\n"), r.testes.includes("terminou bem") ? "ok" : "falhou");
      return;
    }
  }

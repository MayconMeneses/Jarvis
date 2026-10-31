  // ── Meu perfil (☰ > Ajustes): ver, editar e apagar os campos. Mudar gera o CARTÃO de aprovação; nada grava direto. ──
  (() => {
    const $ = (id) => document.getElementById(id);
    const dlg = $("perfil");
    const CAMPOS = [["quem", "Quem sou"], ["projetos", "Projetos"], ["preferencias", "Preferências"], ["tom", "Tom de conversa"], ["metas", "Metas"]];
    const ORIGEM = { definido: "definido por você", deduzido: "deduzido das suas notas" };
    const MAX = 300;
    const api = () => (window.pywebview && window.pywebview.api) || null;
    const dizer = (texto, ok) => { const e = $("pf-info"); e.textContent = texto || ""; e.className = "feedback " + (ok ? "on-ok" : "on-no"); };

    function linha(campo, nome, dado) {
      const sec = document.createElement("section");
      sec.className = "pf-campo";
      const rotulo = document.createElement("label");
      rotulo.htmlFor = "pf-" + campo; rotulo.textContent = nome;
      const origem = document.createElement("small");
      origem.textContent = dado ? "(" + (ORIGEM[dado.origem] || dado.origem) + ")" : "(ainda vazio)";
      const area = document.createElement("textarea");
      area.id = "pf-" + campo; area.rows = 2; area.maxLength = MAX; area.value = dado ? dado.valor : "";
      const botoes = document.createElement("div");
      botoes.className = "pf-botoes";
      const salvar = document.createElement("button");
      salvar.type = "button"; salvar.className = "primary"; salvar.textContent = "Pedir para salvar";
      const apagar = document.createElement("button");
      apagar.type = "button"; apagar.className = "danger"; apagar.textContent = "Pedir para apagar";
      const apagavel = !!dado && dado.origem === "definido";  // o deduzido vem das notas: edita-se lá, em Memória
      apagar.disabled = !apagavel;
      if (!apagavel) apagar.title = "Só dá para apagar o que você definiu. O resto vem das suas notas (Memória).";
      botoes.append(salvar, apagar);
      sec.append(rotulo, origem, area, botoes);
      const pedir = (metodo, args) => async () => {
        const ponte = api();
        if (!ponte) return;
        salvar.disabled = apagar.disabled = true;
        let res;
        try { res = await ponte[metodo](...args()); } catch (e) { res = { error: "Não consegui falar com a Jarvis agora." }; }
        salvar.disabled = false; apagar.disabled = !apagavel;
        if (res.error) return dizer(res.error, false);
        dlg.close();
        mostrarCartoes(res.actions);
        add("jarvis", "Preparei o cartão do seu perfil. Leia e aprove só se concordar.", "perfil");
      };
      salvar.addEventListener("click", pedir("perfil_definir", () => [campo, area.value.trim()]));
      apagar.addEventListener("click", pedir("perfil_apagar", () => [campo]));
      return sec;
    }

    async function abrir() {
      const lista = $("pf-lista");
      lista.replaceChildren(); lista.setAttribute("aria-busy", "true"); dizer("Carregando…", true);
      dlg.showModal();
      const ponte = api();
      let res = { error: "A ponte da Jarvis não está pronta." };
      try { if (ponte) res = await ponte.perfil_usuario(); } catch (e) { res = { error: "Não consegui ler o perfil agora." }; }
      lista.setAttribute("aria-busy", "false");
      if (res.error) return dizer(res.error, false);
      dizer("", true);
      CAMPOS.forEach(([id, nome]) => lista.appendChild(linha(id, (res.campos[id] && res.campos[id].nome) || nome, res.campos[id])));
      lista.querySelector("textarea").focus();
    }
    $("open-perfil").addEventListener("click", abrir);
    $("close-perfil").addEventListener("click", () => dlg.close());
  })();

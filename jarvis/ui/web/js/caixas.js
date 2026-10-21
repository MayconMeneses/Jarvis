  // ── Caixas abaixo do orbe: clima, oportunidades de emprego e últimas notícias (somente leitura, sem IA) ──────────
  // Estados de cada caixa: carregando (esqueleto + aria-busy), vazio, erro (com "Tentar de novo") e ok. Atualiza ao abrir,
  // a cada 15 min (só com a janela visível) e no botão ↻. Texto de notícia/vaga é dado de terceiros: só textContent.
  const CaixasRegras = (() => {
    const hora = (ts) => new Date(Number(ts) * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    // Resposta da ponte -> estado visual da caixa ("erro" também para resposta ausente ou malformada).
    function classificar(r) {
      if (!r || typeof r !== "object" || !Array.isArray(r.itens)) return "erro";
      if (r.estado === "erro" || r.ok === false) return "erro";
      return r.itens.length ? "ok" : "vazio";
    }
    const linkSeguro = (u) => (/^https?:\/\//i.test(String(u || "")) ? String(u) : "");
    return { hora, classificar, linkSeguro };
  })();
  if (typeof module !== "undefined") module.exports = CaixasRegras;

  if (typeof document !== "undefined" && document.getElementById("cx-clima")) (() => {
    const api = () => (window.pywebview && window.pywebview.api) || null;
    const ROTULO = { clima: "o clima", vagas: "as oportunidades", noticias: "as notícias" };
    const emVoo = {};
    function no(tag, texto, cls) { const e = document.createElement(tag); if (texto != null) e.textContent = texto; if (cls) e.className = cls; return e; }

    function botaoLer(caixa, item, msg) {
      const b = no("button", "Ler para mim", "ler");
      b.type = "button"; b.setAttribute("aria-pressed", "false"); b.dataset.estado = "ocioso";
      b.addEventListener("click", () => {
        const original = b.dataset.estado === "original";
        window.Leitura.alternar(b, msg, item, original ? { original: true } : null);
      });
      return b;
    }
    function botaoAbrir(link) {
      const url = CaixasRegras.linkSeguro(link);
      if (!url) return null;
      const b = no("button", "Abrir"); b.type = "button"; b.title = "Abrir no navegador";
      b.addEventListener("click", () => { try { api().open_link(url); } catch (e) { /* sem ponte */ } });
      return b;
    }
    function itemClima(c, msg) {
      const li = no("li", null, "cx-item"), g = no("div", null, "cx-clima"), t = no("div", String(c.agora_c), "cx-temp");
      t.append(no("small", "°C"));
      g.append(t, no("div", c.condicao, "cx-cond"), no("p", `${c.local} · sensação ${c.sensacao_c}°C`, "cx-meta"));
      li.append(g, no("p", `Máx ${c.maxima_c}°C · mín ${c.minima_c}°C · vento ${c.vento_kmh} km/h` + (c.chuva != null ? ` · chuva ${c.chuva}%` : ""), "cx-meta"));
      const ac = no("div", null, "cx-acoes");
      ac.append(botaoLer(null, { tipo: "clima", titulo: "Clima em " + c.local, trecho: c.frase }, msg));
      li.append(ac);
      return li;
    }
    function itemLista(tipo, it, msg) {
      const li = no("li", null, "cx-item");
      li.append(no("p", it.titulo, "cx-titulo"));
      const meta = tipo === "vaga" ? [it.local, it.fonte, it.nota != null ? "nota " + it.nota : ""] : [it.fonte];
      li.append(no("p", meta.filter(Boolean).join(" · "), "cx-meta"));
      const ac = no("div", null, "cx-acoes"), abrir = botaoAbrir(it.link);
      if (abrir) ac.append(abrir);
      ac.append(botaoLer(null, { tipo, titulo: it.titulo, trecho: it.resumo || "" }, msg));
      li.append(ac);
      return li;
    }

    function esqueleto(c) { const e = no("li", null, "cx-esqueleto"); e.append(no("i"), no("i"), no("i")); e.setAttribute("aria-hidden", "true"); c.lista.replaceChildren(e); }
    function mostrar(c, nome, r) {
      const estado = CaixasRegras.classificar(r);
      c.el.setAttribute("aria-busy", "false");
      const msg = c.leitura; msg.textContent = "";
      c.msg.className = "cx-msg"; c.msg.textContent = (r && r.mensagem) || "";
      if (estado === "erro") {
        c.msg.className = "cx-msg erro"; c.msg.textContent = (r && r.mensagem) || "Não consegui atualizar agora.";
        const b = no("button", "Tentar de novo", "cx-vazio-acao"); b.type = "button"; b.addEventListener("click", () => carregar(nome, true));
        c.lista.replaceChildren(no("li", null, "cx-item")); c.lista.firstChild.append(b);
        return;
      }
      if (estado === "vazio") {
        const li = no("li", null, "cx-item");
        if (r.pede_perfil) {
          const b = no("button", "Preencher perfil", "cx-vazio-acao"); b.type = "button";
          b.addEventListener("click", () => { if (typeof ask === "function") ask("Quero preencher meu perfil de vagas: me pergunte minha stack, nível e modalidade.", true); });
          li.append(b);
        }
        c.lista.replaceChildren(...(li.childNodes.length ? [li] : []));
        return;
      }
      const itens = r.itens.map((i) => (nome === "clima" ? itemClima(i, msg) : itemLista(nome === "vagas" ? "vaga" : "noticia", i, msg)));
      c.lista.replaceChildren(...itens);
      if (!r.desatualizado && r.atualizado_em) c.msg.textContent = "Atualizado às " + CaixasRegras.hora(r.atualizado_em) + ".";
      if (nome === "noticias" && window.Briefing) window.Briefing.noticias(r.itens);
    }

    const caixas = {};
    for (const nome of ["clima", "vagas", "noticias"]) {
      const el = document.getElementById("cx-" + nome);
      const leitura = no("p", null, "cx-leitura"); leitura.setAttribute("role", "status"); el.append(leitura);  // anuncia os passos do "Ler para mim"
      caixas[nome] = { el, lista: el.querySelector(".cx-lista"), msg: el.querySelector(".cx-msg"), leitura };
      el.querySelector(".cx-atualizar").addEventListener("click", () => carregar(nome, true));
    }
    async function carregar(nome, forcar) {
      const c = caixas[nome], ponte = api();
      if (emVoo[nome] || !ponte) return;
      emVoo[nome] = true;
      c.el.setAttribute("aria-busy", "true"); c.msg.className = "cx-msg"; c.msg.textContent = "Carregando " + ROTULO[nome] + "…"; esqueleto(c);
      const botao = c.el.querySelector(".cx-atualizar"); botao.disabled = true;
      let r = null;
      try { r = await ponte["info_" + nome](!!forcar); } catch (e) { r = null; }
      emVoo[nome] = false; botao.disabled = false;
      mostrar(c, nome, r);
    }
    const todas = (forcar) => Object.keys(caixas).forEach((n) => carregar(n, forcar));
    window.addEventListener("pywebviewready", () => todas(false));
    periodico(() => todas(false), 900000);  // o cache da ponte decide se vai à internet de novo
    Object.keys(caixas).forEach((n) => { caixas[n].msg.textContent = "Carregando " + ROTULO[n] + "…"; esqueleto(caixas[n]); });
  })();

  // ── Painel de agentes: janela, consulta (polling), painel lateral, "rodar agora" e ligação com o orbe ──
  // Dados de terceiros (descrição de subagente, detalhe de batimento) só entram via textContent.
  const AgentesUI = (() => {
    const E = AgentesEstado, D = AgentesDesenho;
    const dlg = document.getElementById("agentes"), $ = (id) => document.getElementById(id);
    const POLL_ABERTO = 5000, POLL_FECHADO = 30000;
    let dados = null, tFetch = 0, sel = null, timer = 0, raf = 0, ultimoQuadro = 0, ultimoTexto = 0, estrutura = "", largura = 0, rodando = false, erroFetch = false;
    const refs = { itens: new Map(), subs: new Map() };

    function no(tag, texto, cls) { const e = document.createElement(tag); if (texto != null) e.textContent = texto; if (cls) e.className = cls; return e; }
    function bolinha(cor) { const i = no("i", null, "ag-ponto"); i.style.background = cor; return i; }
    const api = () => (window.pywebview && window.pywebview.api) || null;
    const aberto = () => dlg.open;
    const idadeDe = (a) => E.idadeLocal(a, performance.now() - tFetch);
    const achar = (id) => (dados ? dados.agentes.find((a) => a.id === id) : null);
    const acharSub = (id) => (dados ? dados.subagentes.itens.find((s) => "sub:" + s.agent_id === id) : null);
    function dizer(texto, ok) { const i = $("ag-info"); i.textContent = texto || ""; i.className = "feedback " + (ok === false ? "on-no" : "on-ok"); }

    // ── consulta ──────────────────────────────────────────────────────
    async function buscar() {
      const ponte = api();
      if (!ponte || !ponte.agents_status) return;
      try {
        const r = await ponte.agents_status();
        if (!r || !Array.isArray(r.agentes)) throw new Error("resposta inválida");
        r.subagentes = r.subagentes && Array.isArray(r.subagentes.itens) ? r.subagentes : { resumo: {}, itens: [] };
        dados = r; tFetch = performance.now();
        document.body.dataset.agents = E.paraOrbe(r.resumo);
        if (aberto()) { desenharTudo(); if (erroFetch) { dizer(""); erroFetch = false; } }
      } catch (e) {
        if (aberto()) { erroFetch = true; dizer("Não consegui atualizar agora. Mostrando o último retrato.", false); }
      }
    }

    function agendar() {
      clearTimeout(timer);
      timer = setTimeout(async () => { if (!document.hidden) await buscar(); agendar(); }, aberto() ? POLL_ABERTO : POLL_FECHADO);
    }

    // ── desenho ───────────────────────────────────────────────────────
    function montarMapa() {
      const mapa = $("ag-mapa"), w = Math.max(280, Math.round(mapa.clientWidth || 320));
      largura = w;
      D.definir(dados.agentes, dados.subagentes.itens, tFetch);
      D.montar($("ag-svg"), w, Math.round(Math.min(440, Math.max(300, w * 0.95))), escolher);
      D.selecionar(sel);
      estrutura = D.estrutura();
    }

    function desenharTudo() {
      D.definir(dados.agentes, dados.subagentes.itens, tFetch);
      if (!largura || estrutura !== D.estrutura()) montarMapa();
      if (sel && !achar(sel) && !acharSub(sel)) sel = null;
      desenharResumo(); desenharLista(); desenharSubs(); desenharDetalhe();
      D.quadro(performance.now());
    }

    function desenharResumo() {
      const r = dados.resumo || {}, s = dados.subagentes.resumo || {}, u = dados.uso;
      const partes = [`${r.total || 0} agentes: ${r.ok || 0} em dia, ${r.atencao || 0} pedindo atenção, ${r.off || 0} desligados.`];
      if (s.total) partes.push(`Claude Code: ${s.rodando || 0} subagente(s) rodando de ${s.total} na última hora.`);
      partes.push(u ? `Uso de IA hoje: ${Math.round((u.tokens_out || 0) / 1000)} k de saída${u.custo_usd != null ? ", valor equivalente ~US$ " + u.custo_usd.toFixed(2).replace(".", ",") + " (estimado)" : ""}.` : "Uso de IA hoje: sem dado.");
      const el = $("ag-resumo");
      el.textContent = partes.join(" ");
      el.className = "ag-resumo " + (r.pior === "error" ? "erro" : r.atencao ? "atencao" : "ok");
    }

    function desenharLista() {
      refs.itens.clear();
      $("ag-lista").replaceChildren(...dados.agentes.map((a) => {
        const li = no("li"), b = no("button", null, "ag-item");
        b.type = "button";
        const v = E.visual(a, idadeDe(a));
        const nome = no("span", a.nome, "ag-nome"), est = no("small", null, "ag-estado");
        b.append(bolinha(v.cor), nome, est);
        b.addEventListener("click", () => escolher(a.id));
        li.append(b);
        refs.itens.set(a.id, { b, est, ponto: b.firstChild });
        return li;
      }));
      textosVivos();
    }

    function desenharSubs() {
      refs.subs.clear();
      const itens = dados.subagentes.itens;
      $("ag-subs-sec").hidden = !itens.length;
      $("ag-subs").replaceChildren(...itens.slice(0, 12).map((s) => {
        const li = no("li"), b = no("button", null, "ag-item"), sv = E.satelite(s, Date.now() / 1000);
        b.type = "button";
        b.append(bolinha(sv.cor), no("span", s.tipo || "subagente", "ag-nome"), no("small", sv.rotulo + " · " + E.fmtDuracao(s.duracao_s), "ag-estado"));
        b.addEventListener("click", () => escolher("sub:" + s.agent_id));
        li.append(b);
        refs.subs.set("sub:" + s.agent_id, b);
        return li;
      }));
      marcarSelecao();
    }

    // Textos que mudam a cada segundo (idade corre sozinha entre as consultas).
    function textosVivos() {
      if (!dados) return;
      dados.agentes.forEach((a) => {
        const r = refs.itens.get(a.id);
        if (!r) return;
        const idade = idadeDe(a), v = E.visual(a, idade);
        const m = E.metrica(a, idade, v);
        r.est.textContent = m ? v.rotulo + " · " + m : v.rotulo;
        r.ponto.style.background = v.cor;
      });
      if (sel && sel.slice(0, 4) !== "sub:") atualizarIdadeDetalhe();
    }

    function marcarSelecao() {
      refs.itens.forEach((r, id) => r.b.setAttribute("aria-current", String(id === sel)));
      refs.subs.forEach((b, id) => b.setAttribute("aria-current", String(id === sel)));
    }

    // ── detalhe do selecionado ────────────────────────────────────────
    function linha(rotulo, valor, id) { const d = no("div"); const v = no("dd", valor); if (id) v.id = id; d.append(no("dt", rotulo), v); return d; }

    function detalheAgente(a) {
      const idade = idadeDe(a), v = E.visual(a, idade), cx = no("div");
      const dl = no("dl", null, "ag-dl");
      dl.append(linha("Estado", v.rotulo + (v.estado === "idle" ? " (parado de propósito)" : "")),
        linha("Último sinal", E.fmtIdade(idade), "ag-d-idade"),
        linha("Próxima rodada", a.cadencia_s && v.estado !== "off" ? "em " + E.fmtDuracao(E.proximoEm(a, idade)) : "—", "ag-d-prox"),
        linha("Cadência", a.cadencia_s ? "a cada " + E.fmtDuracao(a.cadencia_s) : "contínuo"));
      if (a.detalhe) dl.append(linha("Detalhe", a.detalhe));
      cx.append(no("p", a.faz, "ag-faz"), dl);
      if (a.acao) {
        const b = no("button", "Rodar agora", "primary");
        b.type = "button"; b.id = "ag-rodar"; b.disabled = rodando;
        b.addEventListener("click", () => rodar(a));
        cx.append(b);
      }
      return cx;
    }

    function detalheSub(s) {
      const sv = E.satelite(s, Date.now() / 1000), t = s.tokens || {}, dl = no("dl", null, "ag-dl");
      dl.append(linha("Estado", sv.rotulo + (s.inferido ? " (deduzido pelo horário do arquivo)" : "")),
        linha("Projeto", s.projeto || "—"), linha("Duração", E.fmtDuracao(s.duracao_s)),
        linha("Ferramentas", s.ferramentas == null ? "—" : String(s.ferramentas)),
        linha("Tokens", sv.tokens + (t.origem ? " (" + t.origem + ")" : "")), linha("Custo", sv.custo));
      const cx = no("div");
      cx.append(no("p", s.descricao || "Sem descrição.", "ag-faz"), dl);
      return cx;
    }

    function desenharDetalhe() {
      const alvo = $("ag-detalhe"), a = achar(sel), s = acharSub(sel);
      if (!a && !s) { alvo.replaceChildren(no("p", "Toque num agente na constelação ou na lista para ver o detalhe.", "ag-faz")); return; }
      alvo.replaceChildren(no("h3", a ? a.nome : "Subagente: " + (s.tipo || "Claude Code")), a ? detalheAgente(a) : detalheSub(s));
      marcarSelecao();
    }

    function atualizarIdadeDetalhe() {
      const a = achar(sel), i = $("ag-d-idade"), p = $("ag-d-prox");
      if (!a || !i) return;
      const idade = idadeDe(a);
      i.textContent = E.fmtIdade(idade);
      if (p && a.cadencia_s && E.visual(a, idade).estado !== "off") p.textContent = "em " + E.fmtDuracao(E.proximoEm(a, idade));
    }

    function escolher(id) {
      sel = sel === id ? null : id;
      D.selecionar(sel);
      if (dados) desenharDetalhe();
    }

    // ── "rodar agora": só pela lista branca do backend; avisa o que de fato aconteceu ──
    async function rodar(a) {
      const ponte = api();
      if (!ponte || !ponte.agents_run || rodando) return;
      rodando = true; dizer("Rodando " + a.nome + "…"); desenharDetalhe();
      try {
        const r = await ponte.agents_run(a.id);
        await buscar();
        const novo = achar(a.id);
        const mudou = r.ok && novo && novo.last_ts != null && (r.ts_antes == null || novo.last_ts > r.ts_antes);
        dizer(!r.ok ? r.mensagem : mudou ? r.mensagem : r.mensagem + " O batimento ainda não mudou; confira de novo em instantes.", !!r.ok && mudou);
      } catch (e) { dizer("Não consegui rodar agora.", false); }
      rodando = false;
      if (dados) desenharDetalhe();
    }

    // ── relógio de quadros: só com a janela aberta e a aba visível ─────────
    function modoFx() { return window.Orbe ? window.Orbe.modoEfetivo() : "completo"; }
    function laco(t) {
      raf = 0;
      if (!aberto() || document.hidden) return;
      const fx = modoFx(); D.modo(fx);
      const intervalo = fx === "desligado" ? 1000 : fx === "suave" ? 100 : 33;
      if (t - ultimoQuadro >= intervalo) { ultimoQuadro = t; D.quadro(t); }
      if (t - ultimoTexto >= 1000) { ultimoTexto = t; textosVivos(); }
      raf = requestAnimationFrame(laco);
    }
    function ligarLaco() { if (!raf && aberto() && !document.hidden) raf = requestAnimationFrame(laco); }
    function pararLaco() { if (raf) cancelAnimationFrame(raf); raf = 0; }

    function abrir() {
      dlg.showModal(); largura = 0;
      if (dados) requestAnimationFrame(() => { desenharTudo(); ligarLaco(); }); else ligarLaco();
      buscar().then(() => { if (aberto()) { if (!dados) dizer("Sem resposta do painel.", false); ligarLaco(); } });
      agendar();
    }
    function fechar() { dlg.close(); }
    dlg.addEventListener("close", () => { pararLaco(); rodando = false; agendar(); });
    dlg.addEventListener("cancel", () => pararLaco());

    document.addEventListener("visibilitychange", () => { if (document.hidden) pararLaco(); else { buscar(); ligarLaco(); } });
    if (window.ResizeObserver) {
      let espera = 0;
      new ResizeObserver(() => {
        clearTimeout(espera);
        espera = setTimeout(() => { if (aberto() && dados && Math.abs($("ag-mapa").clientWidth - largura) > 8) { largura = 0; desenharTudo(); } }, 120);
      }).observe($("ag-mapa"));
    }
    if (window.Orbe) window.Orbe.aoMudar(() => { if (aberto() && dados) { D.modo(modoFx()); D.quadro(performance.now()); } });
    $("open-agentes").addEventListener("click", abrir);
    $("close-agentes").addEventListener("click", fechar);
    $("ag-atualizar").addEventListener("click", buscar);
    window.addEventListener("pywebviewready", () => { buscar(); agendar(); });

    return { buscar, abrir, escolher, estado: () => ({ sel, aberto: aberto(), rafAtivo: raf !== 0, dados }) };
  })();

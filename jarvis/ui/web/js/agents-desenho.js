  // ── Painel de agentes: desenho da constelação em SVG (só textContent/atributos; cores só por variáveis do tema) ──
  const AgentesDesenho = (() => {
    const NS = "http://www.w3.org/2000/svg", E = AgentesEstado, TAU = Math.PI * 2;
    const MAX_SAT = 5;
    let svg = null, W = 0, H = 0, cx = 0, cy = 0, nos = [], sats = [], aneis = [], nucleo = null, extra = null;
    let dados = { agentes: [], subs: [], t0: 0 }, fx = "completo", sel = null, aoSelecionar = () => {};

    function el(tag, attrs, pai, estilo) {
      const e = document.createElementNS(NS, tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]);
      if (estilo) Object.assign(e.style, estilo);
      if (pai) pai.append(e);
      return e;
    }
    function texto(pai, y, tam, cor) {
      return el("text", { x: 0, y, "text-anchor": "middle", "font-size": tam }, pai, { fill: cor, stroke: "var(--bg)", strokeWidth: "3px", paintOrder: "stroke" });
    }
    function ativar(g, id) {
      g.setAttribute("tabindex", "0"); g.setAttribute("role", "button"); g.style.cursor = "pointer";
      g.addEventListener("click", () => aoSelecionar(id));
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); aoSelecionar(id); } });
    }

    function montarAneis(raios, nuc, base) {
      for (const [i, raio, trecho, vel] of [[0, nuc + base * 0.12, "5 4", 22], [1, nuc + base * 0.26, "2 7", -34], [2, nuc + base * 0.4, "40 22 8 22", 58]]) {
        const g = el("g", {}, raios);
        el("circle", { cx, cy, r: raio, fill: "none", "stroke-dasharray": trecho, "stroke-width": i === 2 ? 1.6 : 1 }, g, { stroke: "var(--line-strong)", opacity: 0.7 - i * 0.12 });
        aneis.push({ g, vel });
      }
    }

    function montarAgente(a, p, R, nuc, largo, camadas) {
      const d = Math.hypot(p.x - cx, p.y - cy) || 1;
      const raio = el("line", { x1: cx + (p.x - cx) * nuc * 1.05 / d, y1: cy + (p.y - cy) * nuc * 1.05 / d, x2: p.x, y2: p.y, "stroke-width": 1 }, camadas.ligacoes, { stroke: "var(--line)" });
      const pulso = el("circle", { r: 2.6, cx: p.x, cy: p.y }, camadas.luz, { fill: "var(--ok)", opacity: 0 });
      const g = el("g", { transform: `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})` }, svg);
      const aro = el("polygon", { points: E.hexagono(0, 0, R + 10), "stroke-width": 1.5, "stroke-dasharray": "3 3" }, g, { fill: "none", stroke: "var(--text)", display: "none" });
      el("circle", { r: R + 6, fill: "none", "stroke-width": 1.5 }, g, { stroke: "var(--line)" });
      const arco = el("path", { d: "", fill: "none", "stroke-width": 2.6, "stroke-linecap": "round" }, g);
      const hex = el("polygon", { points: E.hexagono(0, 0, R), "stroke-width": 2 }, g, { fill: "var(--panel-solid)" });
      const ico = el("text", { x: 0, y: 0, "text-anchor": "middle", "dominant-baseline": "central", "font-size": Math.round(R * 0.85) }, g, { fill: "var(--text)" });
      ico.textContent = E.ICONE[a.id] || "•";
      texto(g, R + 19, 12, "var(--text)").textContent = E.CURTO[a.id] || a.nome;
      const met = largo ? texto(g, R + 32, 11, "var(--muted)") : null;
      el("title", {}, g).textContent = a.nome;
      ativar(g, a.id);
      return { a, p, R, g, aro, arco, hex, raio, pulso, met, ultimoMet: "" };
    }

    function montarSatelites() {
      const sessoes = nos.find((x) => x.a.id === "sessoes");
      if (!sessoes) return;
      const orb = el("g", {}, svg);
      dados.subs.slice(0, MAX_SAT).forEach((s, i) => {
        const g = el("g", {}, orb), c = el("circle", { r: 4.6, "stroke-width": 1.4 }, g, { fill: "var(--panel-solid)" });
        el("circle", { r: 10, fill: "transparent" }, g);
        el("title", {}, g).textContent = (s.tipo || "subagente") + " · " + E.satelite(s, Date.now() / 1000).rotulo;
        ativar(g, "sub:" + s.agent_id);
        sats.push({ s, g, c, i, no: sessoes });
      });
      if (dados.subs.length > MAX_SAT) {
        extra = texto(el("g", { transform: `translate(${sessoes.p.x.toFixed(1)} ${sessoes.p.y.toFixed(1)})` }, svg), -sessoes.R - 16, 11, "var(--muted)");
        extra.textContent = "+" + (dados.subs.length - MAX_SAT);
      }
    }

    function montar(elemento, largura, altura, aoClicar) {
      svg = elemento; W = Math.round(largura); H = Math.round(altura); aoSelecionar = aoClicar || aoSelecionar;
      cx = W / 2; cy = H / 2;
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      svg.replaceChildren();
      nos = []; sats = []; aneis = []; extra = null;
      const largo = W >= 520, R = W < 420 ? 15 : 19;
      const rx = W / 2 - (largo ? 64 : 46), ry = H / 2 - 44;
      const base = Math.min(rx, ry), nuc = base * 0.27;
      const pos = E.posicoes(dados.agentes.length, cx, cy, rx, ry);
      montarAneis(el("g", {}, svg), nuc, base);
      const camadas = { ligacoes: el("g", {}, svg), luz: el("g", {}, svg) };
      nucleo = el("polygon", { points: E.hexagono(cx, cy, nuc), "stroke-width": 2 }, svg, { fill: "var(--panel-solid)", stroke: "var(--cyan)" });
      el("polygon", { points: E.hexagono(cx, cy, nuc * 0.55), "stroke-width": 1 }, svg, { fill: "none", stroke: "var(--line-strong)" });
      dados.agentes.forEach((a, i) => nos.push(montarAgente(a, pos[i], R, nuc, largo, camadas)));
      montarSatelites();
      selecionar(sel);
    }

    function selecionar(id) {
      sel = id;
      nos.forEach((n) => { n.aro.style.display = n.a.id === id ? "" : "none"; });
      sats.forEach((s) => { s.c.style.strokeWidth = id === "sub:" + s.s.agent_id ? "3px" : ""; });
    }

    function quadroAgente(n, i, t, seg, anima, parado) {
      const idade = E.idadeLocal(n.a, t - dados.t0), v = E.visual(n.a, idade);
      n.hex.style.stroke = v.cor; n.arco.style.stroke = v.cor;
      n.g.style.opacity = v.apagado ? 0.5 : v.erroPulsa && !parado ? 0.6 + 0.4 * Math.sin(seg * 5) : 1;
      const ini = v.modo === "giro" && anima ? (seg * 2.6) % TAU : 0;
      const larg = v.arcoPulsa && !parado ? 3.2 + 1.2 * Math.sin(seg * 6) : 2.6;
      n.arco.setAttribute("d", v.modo === "nenhum" ? "" : E.arcoPath(0, 0, n.R + 6, ini, v.arco));
      n.arco.setAttribute("stroke-width", larg.toFixed(2));
      n.raio.style.stroke = v.erroPulsa ? "var(--danger)" : "";
      n.raio.setAttribute("stroke-dasharray", v.erroPulsa ? "4 4" : "");
      if (v.pulsoLuz && anima) {
        const u = ((seg + i * 0.83) % 3.4) / 3.4;
        n.pulso.setAttribute("cx", (n.p.x + (cx - n.p.x) * u * 0.8).toFixed(1));
        n.pulso.setAttribute("cy", (n.p.y + (cy - n.p.y) * u * 0.8).toFixed(1));
        n.pulso.style.opacity = (Math.sin(u * Math.PI) * 0.9).toFixed(2);
      } else n.pulso.style.opacity = 0;
      if (n.met) {
        const m = E.metrica(n.a, idade, v);
        if (m !== n.ultimoMet) { n.ultimoMet = m; n.met.textContent = m; }
      }
      return v.erroPulsa;
    }

    // Um quadro. t = performance.now(). "desligado": desenha parado; "suave": sem giro nem luz viajando.
    function quadro(t) {
      if (!svg) return;
      const seg = t / 1000, anima = fx === "completo", parado = fx === "desligado";
      aneis.forEach((r) => { if (anima) r.g.setAttribute("transform", `rotate(${((seg * r.vel) % 360).toFixed(2)} ${cx} ${cy})`); else r.g.removeAttribute("transform"); });
      let erro = false;
      nos.forEach((n, i) => { erro = quadroAgente(n, i, t, seg, anima, parado) || erro; });
      nucleo.style.stroke = erro ? "var(--danger)" : "var(--cyan)";
      const agora = Date.now() / 1000;
      sats.forEach((s) => {
        const sv = E.satelite(s.s, agora), rodando = s.s.estado === "rodando";
        const n = Math.min(MAX_SAT, dados.subs.length);
        const ang = -Math.PI / 2 + (anima ? 1.2 * Math.sin(seg * (rodando ? 0.9 : 0.3) + s.i * 2.1) : (s.i - (n - 1) / 2) * 0.6);  // balança acima do agente, longe do nome
        const raio = s.no.R + 15 + (s.i % 2) * 7;
        s.g.setAttribute("transform", `translate(${(s.no.p.x + raio * Math.cos(ang)).toFixed(1)} ${(s.no.p.y + raio * Math.sin(ang)).toFixed(1)})`);
        s.c.style.stroke = sv.cor; s.g.style.opacity = sv.opacidade;
      });
    }

    function definir(agentes, subs, t0) { dados = { agentes, subs, t0 }; }
    const estrutura = () => dados.agentes.map((a) => a.id).join() + "|" + dados.subs.slice(0, MAX_SAT + 1).map((s) => s.agent_id).join();
    return { montar, quadro, selecionar, definir, modo: (m) => { fx = m; }, estrutura, tamanho: () => [W, H] };
  })();

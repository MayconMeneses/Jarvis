  // ── Layout das caixas arrastáveis: regras PURAS (sem DOM, testáveis no Node) ────────────────────────────────
  // Posição salva = fração 0..1 do espaço livre da área (x = 0 encosta à esquerda, 1 à direita). Assim a caixa nunca
  // sai da janela, mesmo se a janela mudar de tamanho. A zona proibida é o retângulo do orbe/cartão central.
  const LayoutSalvo = (() => {
    const IDS = ["telemetria", "sessoes", "uso", "tarefas", "emails", "agentes", "canal", "clima", "vagas", "noticias", "tecnologia"];
    const ok01 = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 1;
    const num = (v) => typeof v === "number" && Number.isFinite(v);

    // JSON antigo, corrompido ou hostil -> só {id conhecido: {x, y}} válidos. Nunca lança.
    function sanear(bruto) {
      const saida = {};
      if (!bruto || typeof bruto !== "object" || Array.isArray(bruto)) return saida;
      for (const id of IDS) {
        const p = Object.prototype.hasOwnProperty.call(bruto, id) ? bruto[id] : null;
        if (p && typeof p === "object" && ok01(p.x) && ok01(p.y)) saida[id] = { x: p.x, y: p.y };
      }
      return saida;
    }
    const limitar = (r, area) => ({
      x: Math.min(Math.max(0, r.x), Math.max(0, area.w - r.w)), y: Math.min(Math.max(0, r.y), Math.max(0, area.h - r.h)), w: r.w, h: r.h,
    });
    const cruza = (a, b) => !!b && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
    const dentro = (r, area) => r.x >= 0 && r.y >= 0 && r.x + r.w <= area.w && r.y + r.h <= area.h;

    // Põe a caixa dentro da janela e fora da zona proibida, pelo menor deslocamento (esquerda/direita/acima/abaixo).
    // Devolve {x, y, empurrada, rejeitada}; rejeitada = nenhum lugar livre (o chamador volta para onde estava).
    function resolver(r, area, zona) {
      const c = limitar(r, area);
      if (!cruza(c, zona)) return { x: c.x, y: c.y, empurrada: c.x !== r.x || c.y !== r.y, rejeitada: false };
      const cand = [{ ...c, x: zona.x - c.w }, { ...c, x: zona.x + zona.w }, { ...c, y: zona.y - c.h }, { ...c, y: zona.y + zona.h }]
        .map((k) => limitar(k, area)).filter((k) => !cruza(k, zona));
      if (!cand.length) return { x: r.x, y: r.y, empurrada: false, rejeitada: true };
      cand.sort((a, b) => Math.hypot(a.x - c.x, a.y - c.y) - Math.hypot(b.x - c.x, b.y - c.y));
      return { x: cand[0].x, y: cand[0].y, empurrada: true, rejeitada: false };
    }
    // Fração salva <-> pixels (tamanho da caixa e da área atuais).
    function dePixels(r, area) {
      const lx = area.w - r.w, ly = area.h - r.h, f = (v, l) => (l > 0 ? Math.min(1, Math.max(0, v / l)) : 0);
      return { x: f(r.x, lx), y: f(r.y, ly) };
    }
    function paraPixels(p, tam, area) {
      return limitar({ x: p.x * (area.w - tam.w), y: p.y * (area.h - tam.h), w: tam.w, h: tam.h }, area);
    }
    // Teclas: setas movem 16 px, Shift+setas 64 px. Outras teclas não movem (null).
    function passo(tecla, shift) {
      const n = shift ? 64 : 16, d = { ArrowLeft: [-n, 0], ArrowRight: [n, 0], ArrowUp: [0, -n], ArrowDown: [0, n] }[tecla];
      return d ? { dx: d[0], dy: d[1] } : null;
    }
    function anuncio(nome, r, area) {
      const lx = Math.max(1, area.w - r.w), ly = Math.max(1, area.h - r.h);
      return `${nome}: ${Math.round((r.x / lx) * 100)}% da esquerda, ${Math.round((r.y / ly) * 100)}% do topo.`;
    }
    return { IDS, sanear, limitar, cruza, dentro, resolver, dePixels, paraPixels, passo, anuncio, num };
  })();
  if (typeof module !== "undefined") module.exports = LayoutSalvo;

  // ── cores do tema para os desenhos em canvas (que não enxergam o CSS): lidas dos tokens e guardadas até o tema mudar ──
  window.Cores = (() => {
    const NOMES = ["text", "muted", "faint", "cyan", "orange", "magenta", "ok", "danger", "bg", "panel-solid", "glow"];
    let cache = null;
    // Qualquer cor CSS (hex, var, color-mix) vira "rgb(r, g, b)" pelo próprio navegador.
    function normalizar(valor) {
      const e = document.createElement("i");
      e.style.color = valor; document.body.append(e);
      const c = getComputedStyle(e).color; e.remove();
      return c;
    }
    function ler() {
      if (cache) return cache;
      const css = getComputedStyle(document.documentElement);
      cache = {};
      for (const n of NOMES) cache[n] = normalizar(css.getPropertyValue("--" + n).trim() || "#888");
      cache.rgb = css.getPropertyValue("--cyan-rgb").trim() || "63, 208, 255";
      return cache;
    }
    // "rgb(1, 2, 3)" + alfa -> "rgba(1, 2, 3, a)"
    const alfa = (cor, a) => cor.replace(/^rgb\(([^)]*)\)$/, `rgba($1, ${a})`);
    // Série de cores para gráficos: só tokens do tema, na ordem de leitura.
    const serie = (i) => { const t = ler(); return [t.cyan, t.orange, t.magenta, t.ok, t.text, t.muted, t.danger, t.faint][i % 8]; };
    window.addEventListener("jarvis-tema", () => { cache = null; });
    return { ler, alfa, serie };
  })();

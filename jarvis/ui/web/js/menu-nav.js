  // ── Menu ☰: regras PURAS de navegação por teclado (sem DOM, testável no Node) ──────────────────────────────
  const MenuNav = (() => {
    // Índice do próximo item para a tecla (setas circulares, Home/End). Devolve null se a tecla não navega.
    function proximo(atual, total, tecla) {
      if (!(total > 0)) return null;
      if (tecla === "ArrowDown") return atual < 0 ? 0 : (atual + 1) % total;
      if (tecla === "ArrowUp") return atual < 0 ? total - 1 : (atual - 1 + total) % total;
      if (tecla === "Home") return 0;
      if (tecla === "End") return total - 1;
      return null;
    }
    const base = (t) => String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/^[^\p{L}\p{N}]+/u, "").toLowerCase();
    // Tipo-a-letra: próximo item (depois do atual, circular) cujo rótulo começa com a letra; -1 se nenhum.
    function porLetra(rotulos, atual, letra) {
      const l = base(letra);
      if (l.length !== 1) return -1;
      const n = rotulos.length;
      for (let k = 1; k <= n; k++) { const i = (Math.max(atual, -1) + k) % n; if (base(rotulos[i]).startsWith(l)) return i; }
      return -1;
    }
    return { proximo, porLetra, base };
  })();
  if (typeof module !== "undefined") module.exports = MenuNav;

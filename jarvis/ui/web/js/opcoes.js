  // ── Regras PURAS dos botões do chat (sem DOM, testáveis no Node): opções do "Você quis dizer" e atalhos ──────────
  const Opcoes = (() => {
    const LIMITE = 3, MAX_ROTULO = 80;
    // "Você quis dizer:\n1. abrir\n2. ..." + "Responda 1, 2 ou 3": devolve [{n, rotulo}] (até 3), ou [] se o texto não for essa pergunta.
    function extrair(texto) {
      const t = String(texto || "");
      if (!/Responda 1/.test(t)) return [];
      const achadas = [];
      for (const linha of t.split(/\r?\n/)) {
        const m = linha.match(/^\s*([1-3])\.\s+(\S.*)$/);
        if (!m || Number(m[1]) !== achadas.length + 1) continue;
        achadas.push({ n: achadas.length + 1, rotulo: m[2].trim().slice(0, MAX_ROTULO) });
        if (achadas.length === LIMITE) break;
      }
      return achadas;
    }
    // Texto que o botão "Pesquisar na internet" envia pelo mesmo caminho de sempre.
    function pesquisa(pedido) {
      const p = String(pedido || "").replace(/\s+/g, " ").trim().slice(0, 120);
      return p ? "pesquisa " + p : "";
    }
    // Atalho vindo do backend → {rotulo, tipo, alvo} ou null. Só a ação conhecida "cerebros" e links http(s).
    function atalho(a) {
      if (!a || typeof a !== "object" || typeof a.rotulo !== "string" || !a.rotulo.trim()) return null;
      const rotulo = a.rotulo.trim().slice(0, 60);
      if (a.acao === "cerebros") return { rotulo, tipo: "acao", alvo: "cerebros" };
      if (typeof a.url === "string" && /^https?:\/\//i.test(a.url)) return { rotulo, tipo: "url", alvo: a.url };
      return null;
    }
    const atalhos = (lista) => (Array.isArray(lista) ? lista.map(atalho).filter(Boolean) : []);
    return { extrair, pesquisa, atalho, atalhos };
  })();
  if (typeof module !== "undefined") module.exports = Opcoes;

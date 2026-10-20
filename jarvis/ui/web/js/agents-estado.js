  // ── Painel de agentes: regras PURAS (estado → cor/arco/pulso, relógio local, posições). Sem DOM, testável no Node ──
  const AgentesEstado = (() => {
    const COR = { ok: "var(--ok)", stale: "var(--orange)", error: "var(--danger)", idle: "var(--cyan)", off: "var(--faint)" };
    const ROTULO = { ok: "Em dia", stale: "Parado", error: "Erro", idle: "Em espera", off: "Desligado" };
    const CURTO = { proativo: "Iniciativa", autonomo: "Estudo", avaliacao_semanal: "Avaliação", sessoes: "Sessões", tarefas: "Tarefas",
      atualizador: "Atualizador", celular: "Celular", voz: "Voz", llm_local: "Cérebro local" };
    const ICONE = { proativo: "!", autonomo: "✦", avaliacao_semanal: "%", sessoes: "▤", tarefas: "≡", atualizador: "↻", celular: "▯", voz: "♪", llm_local: "◈" };
    const STALE_FATOR = 2.5, LIMIAR_PULSO = 0.92, ARCO_CONTINUO = 0.25;
    const COR_SAT = { rodando: "var(--cyan)", concluido: "var(--ok)", falhou: "var(--danger)", parado: "var(--faint)", inativo: "var(--faint)" };
    const ROTULO_SAT = { rodando: "Rodando", concluido: "Concluído", falhou: "Falhou", parado: "Parado", inativo: "Inativo" };

    const limitar = (v, a, b) => Math.min(b, Math.max(a, v));

    // Idade de agora: a do servidor + o tempo corrido desde o fetch (o relógio anda sozinho entre as consultas).
    function idadeLocal(a, msDesdeFetch) {
      return a.age_s == null ? null : Math.max(0, a.age_s + Math.max(0, msDesdeFetch) / 1000);
    }

    // Estado mostrado: o do servidor, mas "ok" vira "stale" se a idade local já passou de 2,5x a cadência.
    function estadoLocal(a, idade) {
      if (a.state === "ok" && a.cadencia_s && idade != null && idade > STALE_FATOR * a.cadencia_s) return "stale";
      return COR[a.state] ? a.state : "stale";
    }

    // Visual completo de um agente num instante. modo: "arco" (ciclo), "giro" (contínuo) ou "nenhum".
    function visual(a, idade) {
      const estado = estadoLocal(a, idade);
      const ciclico = a.modo === "ciclico" && a.cadencia_s > 0;
      let modo = "nenhum", arco = 0;
      if (estado !== "off") {
        if (ciclico && idade != null) { modo = "arco"; arco = estado === "stale" || estado === "error" ? 1 : limitar(idade / a.cadencia_s, 0, 1); }
        else if (!ciclico && (estado === "ok" || estado === "idle")) { modo = "giro"; arco = ARCO_CONTINUO; }
        else if (estado === "error") { modo = "arco"; arco = 1; }
      }
      return { estado, cor: COR[estado], rotulo: ROTULO[estado], modo, arco,
        arcoPulsa: modo === "arco" && estado === "ok" && arco > LIMIAR_PULSO,
        pulsoLuz: estado === "ok",      // luz viajando até o núcleo: só de agente saudável
        erroPulsa: estado === "error", apagado: estado === "off" };
    }

    function fmtDuracao(s) {
      if (s == null) return "—";
      s = Math.round(s);
      if (s < 60) return s + " s";
      if (s < 3600) return Math.floor(s / 60) + " min";
      if (s < 86400) return Math.floor(s / 3600) + " h" + (Math.floor((s % 3600) / 60) ? " " + Math.floor((s % 3600) / 60) + " min" : "");
      return Math.floor(s / 86400) + " d";
    }
    const fmtIdade = (s) => (s == null ? "sem registro" : "há " + fmtDuracao(s));

    // Métrica curta sob o nome do agente.
    function metrica(a, idade, v) {
      if (v.estado === "off") return "";
      if (v.estado === "error") return "erro " + fmtIdade(idade);
      if (idade == null) return v.estado === "idle" ? "em espera" : "sem sinal";
      if (a.modo === "continuo" && !a.cadencia_s) return v.estado === "ok" ? "no ar" : "em espera";
      if (v.estado === "stale") return "parado " + fmtIdade(idade);
      return "últ. " + fmtDuracao(idade);
    }

    function proximoEm(a, idade) {
      if (!a.cadencia_s || idade == null) return null;
      return Math.max(0, a.cadencia_s - idade);
    }

    // Rótulo do orbe: o pior estado do resumo do servidor.
    function paraOrbe(resumo) {
      if (!resumo) return "";
      if (resumo.pior === "error") return "erro";
      return resumo.atencao > 0 || resumo.pior === "stale" ? "atencao" : "ok";
    }

    // Posição dos n agentes numa elipse (começa no topo, sentido horário).
    function posicoes(n, cx, cy, rx, ry) {
      return Array.from({ length: n }, (_, i) => {
        const ang = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(1, n);
        return { x: cx + rx * Math.cos(ang), y: cy + ry * Math.sin(ang), ang };
      });
    }

    function hexagono(cx, cy, r) {
      return Array.from({ length: 6 }, (_, i) => {
        const a = -Math.PI / 2 + (i * Math.PI) / 3;
        return (cx + r * Math.cos(a)).toFixed(1) + "," + (cy + r * Math.sin(a)).toFixed(1);
      }).join(" ");
    }

    // Arco circular (ângulos em rad, 0 = topo, horário). Arco completo vira dois semiarcos (SVG não fecha 360°).
    function arcoPath(cx, cy, r, ini, fracao) {
      const f = limitar(fracao, 0, 1);
      if (f <= 0) return "";
      const pt = (a) => (cx + r * Math.sin(a)).toFixed(2) + " " + (cy - r * Math.cos(a)).toFixed(2);
      if (f >= 0.9999) return `M ${pt(ini)} A ${r} ${r} 0 1 1 ${pt(ini + Math.PI)} A ${r} ${r} 0 1 1 ${pt(ini + 2 * Math.PI)}`;
      const fim = ini + f * 2 * Math.PI;
      return `M ${pt(ini)} A ${r} ${r} 0 ${f > 0.5 ? 1 : 0} 1 ${pt(fim)}`;
    }

    // Satélite (subagente do Claude Code): cor, opacidade que some depois de terminar e rótulo de custo SEMPRE "estimado".
    function satelite(s, agora) {
      const fimIdade = s.estado === "rodando" || s.fim == null ? 0 : Math.max(0, agora - s.fim);
      const t = s.tokens || {};
      const custo = t.custo_usd == null ? "custo indisponível" : "~US$ " + Number(t.custo_usd).toFixed(2).replace(".", ",") + " (estimado)";
      const total = t.tokens_total || 0;
      const tokens = total >= 1e6 ? (total / 1e6).toFixed(1) + " M" : total >= 1e3 ? (total / 1e3).toFixed(1) + " k" : String(total);
      return { cor: COR_SAT[s.estado] || COR_SAT.inativo, rotulo: ROTULO_SAT[s.estado] || "Inativo",
        opacidade: limitar(1 - fimIdade / 1800, 0.25, 1), custo, tokens: tokens + " tokens" };
    }

    return { COR, ROTULO, CURTO, ICONE, STALE_FATOR, idadeLocal, estadoLocal, visual, fmtDuracao, fmtIdade, metrica, proximoEm,
      paraOrbe, posicoes, hexagono, arcoPath, satelite };
  })();
  if (typeof module !== "undefined") module.exports = AgentesEstado;

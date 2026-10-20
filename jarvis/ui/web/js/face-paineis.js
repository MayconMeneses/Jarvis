  // ── FACE: desenho dos painéis HUD. Só textContent/createElement: o que vem de e-mail ou tarefa é dado de terceiros. ──
  window.FacePaineis = (() => {
    const ESTADOS = { permissao: "PERMISSÃO", pergunta: "PERGUNTA", aguardando: "AGUARDANDO", trabalhando: "TRABALHANDO" };
    const NADA = "—";
    function no(tag, classe, texto) {
      const e = document.createElement(tag);
      if (classe) e.className = classe;
      if (texto !== undefined) e.textContent = String(texto);
      return e;
    }
    function linha(rotulo, valor, classe) {
      const l = no("div", "fp-linha " + (classe || ""));
      l.append(no("span", "fp-rot", rotulo), no("b", "fp-val", valor));
      return l;
    }
    function barra(rotulo, pct) {
      const n = Number(pct), ok = Number.isFinite(n);
      const l = no("div", "fp-barra"), b = no("span", "fp-trilho"), i = no("i");
      i.style.width = (ok ? Math.max(0, Math.min(100, n)) : 0) + "%";
      if (ok && n >= 90) i.className = "crit"; else if (ok && n >= 75) i.className = "warn";
      b.append(i);
      l.append(no("span", "fp-rot", rotulo), b, no("b", "fp-val", ok ? n + "%" : NADA));
      return l;
    }
    function hora(ts) {
      const d = new Date(Number(ts) * 1000);
      return isNaN(d) ? NADA : d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    }
    const montadores = {
      vitals: (d) => [barra("CPU", d.cpu), barra("RAM", d.ram)],
      sessoes: (d) => {
        const c = d.contagem || {};
        const itens = Object.keys(ESTADOS).map((k) => linha(ESTADOS[k], c[k] ?? NADA, k === "permissao" || k === "pergunta" ? "atencao" : ""));
        (d.itens || []).forEach((s) => itens.push(no("div", "fp-item", s.projeto + " · " + (ESTADOS[s.estado] || NADA))));
        return itens;
      },
      status: (d) => [linha("SERVIÇOS OK", d.ok + " de " + d.total), linha("ATENÇÃO", d.atencao, d.atencao ? "atencao" : ""), linha("DESLIGADOS", d.off)],
      emails: (d) => {
        const itens = [linha("NÃO LIDOS", d.total + (d.mais ? "+" : ""))];
        (d.itens || []).forEach((m) => { const e = no("div", "fp-item"); e.append(no("span", "fp-rot", m.de), no("span", "", m.assunto)); itens.push(e); });
        return itens;
      },
      tarefas: (d) => {
        const itens = [linha("RODANDO", d.rodando), linha("NA FILA", d.fila)];
        (d.itens || []).forEach((t) => itens.push(no("div", "fp-item", t.projeto + " · " + t.status + " · " + t.tarefa)));
        return itens;
      },
      logs: (d) => (d.length ? d : []).map((x) => no("div", "fp-item", hora(x.ts) + " " + x.agente + (x.detalhe ? " · " + x.detalhe : ""))),
    };
    // Bloco ausente (null/erro) vira "—"; nunca deixa a tela quebrar.
    function desenhar(dados) {
      for (const nome of Object.keys(montadores)) {
        const alvo = document.getElementById("fp-" + nome);
        if (!alvo) continue;
        let filhos = [];
        try { const d = dados && dados[nome]; if (d !== null && d !== undefined) filhos = montadores[nome](d); } catch (e) { filhos = []; }
        alvo.replaceChildren(...(filhos.length ? filhos : [no("div", "fp-vazio", NADA)]));
      }
    }
    return { desenhar };
  })();

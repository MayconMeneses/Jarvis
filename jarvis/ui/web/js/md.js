  // ── Markdown das respostas, só o subconjunto que a Jarvis usa, montado por DOM (nunca como HTML) ─────────────────
  // Blocos: título (#), lista (- * + 1.), código (```), citação (>), parágrafo. Inline: **negrito**, *itálico*, `código`,
  // [texto](https://...) e URL solta. Link só http/https (javascript:, data: e afins viram texto puro). Texto é sempre nó de texto.
  const Md = (() => {
    const URL_OK = /^https?:\/\/[^\s<>"'\\]+$/i;
    const urlSegura = (u) => { const s = String(u || "").trim(); return URL_OK.test(s) ? s : ""; };
    const RE = /`([^`\n]+)`|\*\*(.+?)\*\*|__(.+?)__|\[([^\]\n]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)|(https?:\/\/[^\s<>"')\]]+)|\*([^*\s][^*\n]*?)\*|(?<![\w])_([^_\s][^_\n]*?)_(?![\w])/g;

    // Texto → nós {t:"x"|"b"|"i"|"c"|"a"}; profundidade limitada para não explodir com entrada hostil.
    function inline(texto, prof = 0) {
      const s = String(texto == null ? "" : texto), saida = [];
      const solto = (v) => { if (v) saida.push({ t: "x", v }); };
      if (prof > 3) { solto(s); return saida; }
      let ultimo = 0, m;
      const re = new RegExp(RE.source, "g");  // uma por chamada: a recursão não pode compartilhar lastIndex
      while ((m = re.exec(s)) !== null) {
        solto(s.slice(ultimo, m.index));
        ultimo = m.index + m[0].length;
        if (m[1] !== undefined) saida.push({ t: "c", v: m[1] });
        else if (m[2] !== undefined || m[3] !== undefined) saida.push({ t: "b", c: inline(m[2] ?? m[3], prof + 1) });
        else if (m[4] !== undefined) {
          const href = urlSegura(m[5]);
          if (href) saida.push({ t: "a", href, v: m[4] }); else solto(m[4]);  // link perigoso: só o rótulo, em texto
        } else if (m[6] !== undefined) {
          const fim = m[6].match(/[.,;:!?]+$/), url = fim ? m[6].slice(0, -fim[0].length) : m[6];
          const href = urlSegura(url);
          if (href) saida.push({ t: "a", href, v: url }); else solto(url);
          if (fim) solto(fim[0]);
        } else saida.push({ t: "i", c: inline(m[7] ?? m[8], prof + 1) });
      }
      solto(s.slice(ultimo));
      return saida;
    }

    // Texto → blocos {t:"h",n,c} | {t:"p",c} | {t:"ul"|"ol",itens:[c]} | {t:"code",v} | {t:"q",c}
    function blocos(texto) {
      const linhas = String(texto == null ? "" : texto).replace(/\r\n?/g, "\n").split("\n"), saida = [];
      let par = [], lista = null, codigo = null;
      const fechaPar = () => { if (par.length) saida.push({ t: "p", c: inline(par.join("\n")) }); par = []; };
      const fechaLista = () => { lista = null; };
      for (const bruta of linhas) {
        if (codigo) {
          if (/^\s*```/.test(bruta)) { saida.push({ t: "code", v: codigo.join("\n") }); codigo = null; } else codigo.push(bruta);
          continue;
        }
        const l = bruta.replace(/\s+$/, "");
        if (/^\s*```/.test(l)) { fechaPar(); fechaLista(); codigo = []; continue; }
        if (!l.trim()) { fechaPar(); fechaLista(); continue; }
        let m = l.match(/^\s{0,3}(#{1,6})\s+(.+)$/);
        if (m) { fechaPar(); fechaLista(); saida.push({ t: "h", n: m[1].length, c: inline(m[2].replace(/\s*#+\s*$/, "")) }); continue; }
        m = l.match(/^\s*([-*+]|\d{1,3}[.)])\s+(.+)$/);
        if (m) {
          fechaPar();
          const tipo = /\d/.test(m[1]) ? "ol" : "ul";
          if (!lista || lista.t !== tipo) { lista = { t: tipo, itens: [] }; saida.push(lista); }
          lista.itens.push(inline(m[2]));
          continue;
        }
        if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(l)) { fechaPar(); fechaLista(); continue; }  // linha horizontal: some
        m = l.match(/^\s*>\s?(.*)$/);
        if (m) { fechaPar(); fechaLista(); saida.push({ t: "q", c: inline(m[1]) }); continue; }
        fechaLista(); par.push(l.trim());
      }
      if (codigo) saida.push({ t: "code", v: codigo.join("\n") });  // cerca sem fim: o que veio até aqui
      fechaPar();
      return saida;
    }

    // Texto puro de nós inline / blocos (legenda curta e leitor de tela: sem asteriscos nem marcação)
    const planoInline = (nos) => nos.map((n) => (n.c ? planoInline(n.c) : n.v)).join("");
    function plano(texto) {
      return blocos(texto).map((b) => (b.itens ? b.itens.map(planoInline).join("; ") : b.v !== undefined ? b.v : planoInline(b.c)))
        .join(" ").replace(/\s+/g, " ").trim();
    }
    // Resumo para a legenda: no máximo `max` caracteres, cortando em fim de palavra. { texto, cortado }
    function resumo(texto, max = 140) {
      const p = plano(texto);
      if (p.length <= max) return { texto: p, cortado: false };
      const corte = p.slice(0, max), esp = corte.lastIndexOf(" ");
      return { texto: (esp > max * 0.5 ? corte.slice(0, esp) : corte).replace(/[\s,;:.\-–]+$/, "") + "…", cortado: true };
    }
    // Uma resposta "simples" cabe na legenda sem o botão Ver mais: um parágrafo curto.
    function simples(texto, max = 140) {
      const b = blocos(texto);
      return b.length <= 1 && (!b[0] || b[0].t === "p") && plano(texto).length <= max;
    }

    // ── DOM ──
    function noInline(pai, nos, aoLink) {
      for (const n of nos) {
        if (n.t === "x") pai.appendChild(document.createTextNode(n.v));
        else if (n.t === "a") {
          const a = document.createElement("a");
          a.href = "#"; a.textContent = n.v.length > 60 ? n.v.slice(0, 57) + "…" : n.v; a.title = n.href;
          a.addEventListener("click", (e) => { e.preventDefault(); aoLink(n.href); });
          pai.appendChild(a);
        } else {
          const el = document.createElement(n.t === "b" ? "strong" : n.t === "i" ? "em" : "code");
          if (n.c) noInline(el, n.c, aoLink); else el.textContent = n.v;
          pai.appendChild(el);
        }
      }
    }
    // Esvazia `el` e desenha o Markdown dentro dele. aoLink(url) abre no navegador padrão (pelo Python).
    function render(el, texto, aoLink) {
      const abrir = aoLink || ((u) => { try { window.pywebview.api.open_link(u); } catch (e) { /* fora da janela */ } });
      el.replaceChildren();
      for (const b of blocos(texto)) {
        let no;
        if (b.t === "h") { no = document.createElement("p"); no.className = "md-h md-h" + Math.min(b.n, 3); noInline(no, b.c, abrir); }
        else if (b.t === "ul" || b.t === "ol") {
          no = document.createElement(b.t);
          b.itens.forEach((c) => { const li = document.createElement("li"); noInline(li, c, abrir); no.appendChild(li); });
        } else if (b.t === "code") { no = document.createElement("pre"); const c = document.createElement("code"); c.textContent = b.v; no.appendChild(c); }
        else { no = document.createElement(b.t === "q" ? "blockquote" : "p"); noInline(no, b.c, abrir); }
        el.appendChild(no);
      }
      return el;
    }
    return { urlSegura, inline, blocos, plano, resumo, simples, render };
  })();
  if (typeof window !== "undefined") window.Md = Md;
  if (typeof module !== "undefined") module.exports = Md;

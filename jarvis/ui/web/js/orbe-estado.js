  // ── Orbe: estado e nível de voz ─────────────────────────────────────
  // Guarda o estado (idle/listening/thinking/speaking), o nível suavizado 0..1 e o modo de efeitos.
  // O desenho fica em orbe.js. Dados reais: envelope da fala (calculado no Python, lido pelo relógio local)
  // e volume do microfone (enviado a ~20 Hz). Contrato do window.onVoice: ver results.js.
  window.Orbe = (() => {
    const NOMES = { idle: "Em espera", listening: "Ouvindo", thinking: "Pensando", speaking: "Falando" };
    const MODOS = ["completo", "suave", "desligado"];
    const s = { estado: "idle", nivel: 0, env: null, t0: 0, dt: 40, atraso: 80, mic: 0, micT: 0, fixo: null, modo: "completo", reduzido: false };
    const reduzido = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    const ouvintes = [];
    const avisar = () => ouvintes.forEach((f) => f());

    function estado(novo) {
      if (!NOMES[novo]) novo = "idle";
      if (s.estado === novo) return;
      s.estado = novo;
      const el = document.getElementById("orbe-estado");
      if (el) el.textContent = NOMES[novo];
      avisar();
    }

    // Entrada única do orbe (mini e FACE): {estado?, nivel?}. nivel numérico (0..1) fixa o nível; null volta ao automático.
    function set(o) {
      if (!o) return;
      if (o.estado !== undefined) estado(o.estado);
      if (o.nivel === null) s.fixo = null; else if (typeof o.nivel === "number") s.fixo = Math.max(0, Math.min(1, o.nivel));
      avisar();
    }

    // Modo efetivo: "completo" vira "suave" quando o sistema pede menos movimento.
    function modoEfetivo() { return s.modo === "completo" && s.reduzido ? "suave" : s.modo; }

    function definirModo(modo, salvar) {
      s.modo = MODOS.includes(modo) ? modo : "completo";
      const sel = document.getElementById("efeitos");
      if (sel) sel.value = s.modo;
      document.documentElement.dataset.efeitos = s.modo;  // a aurora e as animações do CSS seguem este atributo
      if (salvar) {
        try { window.pywebview.api.definir_efeitos_visuais(s.modo); } catch (e) { /* fora da janela (teste) */ }
      }
      avisar();
    }

    // Tratador dos eventos com "tipo" do window.onVoice. Devolve true se era do orbe.
    function evento(ev) {
      if (!ev || !ev.tipo) return false;
      const agora = performance.now();
      if (ev.tipo === "fala") {
        s.env = Array.isArray(ev.env) ? ev.env : [];
        s.t0 = agora; s.dt = ev.dt > 0 ? ev.dt : 40; s.atraso = ev.atraso_ms || 0;
        set({ estado: "speaking" });
      } else if (ev.tipo === "fim") {
        s.env = null;
        if (s.estado === "speaking") set({ estado: typeof busy !== "undefined" && busy ? "thinking" : "idle" });
      } else if (ev.tipo === "mic") {
        s.mic = Math.max(0, Math.min(1, Number(ev.n) || 0)); s.micT = agora;
      }
      return true;
    }

    // Nível desejado agora (0..1) conforme o estado.
    function alvo(agora) {
      if (s.fixo != null) return s.fixo;
      if (s.estado === "speaking") {
        if (s.env === null) return 0.2;
        if (!s.env.length) return 0.4 + 0.25 * Math.sin(agora / 110) * Math.sin(agora / 370);  // sem envelope: ritmo simulado
        const i = (agora - s.t0 - s.atraso) / s.dt;
        if (i < 0 || i >= s.env.length - 1) return 0;
        const k = Math.floor(i), f = i - k;
        return (s.env[k] * (1 - f) + s.env[k + 1] * f) / 100;
      }
      if (s.estado === "listening") return agora - s.micT < 500 ? s.mic : 0.06 + 0.05 * Math.sin(agora / 500);
      if (s.estado === "thinking") return 0.22 + 0.1 * Math.sin(agora / 420);
      return 0;
    }

    // Suavização: ataque rápido (~60 ms) e queda lenta (~220 ms).
    function passo(agora, dtSeg) {
      const a = alvo(agora), tau = a > s.nivel ? 0.06 : 0.22;
      s.nivel += (a - s.nivel) * (1 - Math.exp(-dtSeg / tau));
      return s.nivel;
    }

    if (reduzido) {
      s.reduzido = reduzido.matches;
      const mudou = (e) => { s.reduzido = e.matches; avisar(); };
      if (reduzido.addEventListener) reduzido.addEventListener("change", mudou); else if (reduzido.addListener) reduzido.addListener(mudou);
    }
    const sel = document.getElementById("efeitos");
    if (sel) sel.addEventListener("change", () => definirModo(sel.value, true));
    window.addEventListener("pywebviewready", async () => {
      try { definirModo(await window.pywebview.api.efeitos_visuais(), false); } catch (e) { /* sem ponte */ }
    });

    return { s, estado, set, evento, passo, modoEfetivo, definirModo, aoMudar: (f) => ouvintes.push(f) };
  })();

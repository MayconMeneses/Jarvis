// Toca o áudio PCM do Gemini com Web Audio (a CSP do app não libera <audio src=blob:>). O iOS só deixa o áudio começar depois de um TOQUE do
// usuário: destravar() cria/retoma o contexto dentro do gesto. Se mesmo assim o contexto não rodar, tocar() falha e a saída cai para a voz do aparelho.
// Limite conhecido do iOS: o Web Audio obedece ao botão de silêncio do iPhone (a voz do aparelho, não). Se estiver mudo, a reserva não é acionada: só falta som.
export function criarTocador({ Contexto = globalThis.AudioContext || globalThis.webkitAudioContext } = {}) {
  let ctx = null, fonte = null, fim = null;
  const garantir = () => { if (!ctx && Contexto) ctx = new Contexto(); return ctx; };
  const espera = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(r, ms))]);
  const parar = () => { const f = fonte, x = fim; fonte = fim = null; try { f?.stop(); } catch { /* já parou */ } x?.(); };
  return {
    disponivel: () => Boolean(Contexto),
    // Chame dentro de um toque (clique, envio de mensagem, botão do microfone).
    destravar() {
      try {
        const c = garantir();
        if (!c) return;
        if (c.state !== "running") c.resume?.();
        const b = c.createBuffer(1, 1, c.sampleRate || 24000), s = c.createBufferSource();
        s.buffer = b; s.connect(c.destination); s.start(0);
      } catch { /* sem Web Audio: a reserva (voz do aparelho) cobre */ }
    },
    async tocar({ pcm, taxa }) {
      const c = garantir();
      if (!c) throw new Error("sem Web Audio");
      if (c.state !== "running") await espera(Promise.resolve(c.resume?.()), 1000);
      if (c.state !== "running") throw new Error("áudio bloqueado pelo navegador");
      parar();
      const buf = c.createBuffer(1, pcm.length, taxa), canal = buf.getChannelData(0);
      for (let i = 0; i < pcm.length; i++) canal[i] = pcm[i] / 32768;
      await new Promise((resolver) => {
        const s = c.createBufferSource();
        s.buffer = buf; s.connect(c.destination);
        const prazo = setTimeout(() => parar(), (pcm.length / taxa) * 1000 + 1500);
        const acabou = () => { clearTimeout(prazo); if (fim === acabou) { fim = null; fonte = null; } resolver(); };
        s.onended = acabou; fonte = s; fim = acabou;
        s.start(0);
      });
    },
    parar,
  };
}

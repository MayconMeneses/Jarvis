// Fala do "Ler para mim" com a voz do navegador (SpeechSynthesis), parte por parte, com parar de verdade e Wake Lock opcional.
// No iPhone a fala só é liberada depois de um toque: o Leitor é sempre iniciado por um botão ou por uma mensagem enviada.
const LANGS = { pt: "pt-BR", en: "en-US", es: "es-ES", fr: "fr-FR", de: "de-DE", it: "it-IT" };

export function criarFala({ sintese = globalThis.speechSynthesis, Fala = globalThis.SpeechSynthesisUtterance, nav = globalThis.navigator } = {}) {
  let trava = null, corrente = null;
  const escolherVoz = (lang) => {
    const vozes = sintese.getVoices?.() || [], base = lang.slice(0, 2).toLowerCase();
    return vozes.find((v) => v.lang?.replace("_", "-").toLowerCase() === lang.toLowerCase()) || vozes.find((v) => v.lang?.toLowerCase().startsWith(base)) || null;
  };
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  let geracao = 0;
  // Espera outra fala (por exemplo a resposta do chat) terminar, no máximo 8 s; nunca corta a fala dos outros.
  async function aguardarOcioso() {
    for (const limite = Date.now() + 8000; (sintese.speaking || sintese.pending) && Date.now() < limite;) await esperar(150);
  }
  return {
    disponivel: () => Boolean(sintese && Fala),
    esperar,
    // Termina quando a fala acaba, é cortada ou dá erro. Nunca trava: há um prazo proporcional ao tamanho do texto.
    async falar(texto, { idioma = "pt" } = {}) {
      if (!sintese || !Fala || !texto) return;
      const minha = geracao;
      await aguardarOcioso();
      if (minha !== geracao) return;  // parou enquanto esperava
      await new Promise((resolver) => {
        const lang = LANGS[idioma] || "pt-BR", fala = new Fala(texto), voz = escolherVoz(lang);
        fala.lang = lang;
        if (voz) fala.voice = voz;
        let feito = false, prazo = null;
        const fim = () => { if (feito) return; feito = true; clearTimeout(prazo); if (corrente === fim) corrente = null; resolver(); };
        corrente = fim;
        fala.onend = fala.onerror = fim;
        prazo = setTimeout(fim, Math.max(8000, texto.length * 130));
        try { sintese.speak(fala); } catch { fim(); }
      });
    },
    parar() { geracao++; try { sintese?.cancel(); } catch { /* sem fala */ } corrente?.(); },
    // Mantém a tela acesa durante a leitura, se o navegador permitir. Falhar aqui nunca atrapalha a leitura.
    async manterAcesa(sim) {
      try {
        if (sim && nav?.wakeLock && !trava) trava = await nav.wakeLock.request("screen");
        else if (!sim && trava) { const t = trava; trava = null; await t.release(); }
      } catch { trava = null; }
    },
  };
}

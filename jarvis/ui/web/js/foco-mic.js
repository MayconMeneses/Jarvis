  // ── Microfone do modo foco: botão grande com 5 estados, alimentado por window.onVoice ({escuta: estado}) ──
  // Privacidade: o indicador fica sempre visível no foco; um clique desliga a escuta; o áudio não sai do PC nem vai para disco.
  // Atalhos (só no foco): Espaço = falar agora (sem dizer "Jarvis"), Esc sai do foco (em face.js).
  window.FocoMic = (() => {
    const $ = (id) => document.getElementById(id);
    const caixa = $("foco-mic-caixa"), botao = $("foco-mic"), rotulo = $("foco-mic-rotulo"), agora = $("foco-mic-agora");
    if (!caixa || !botao) return null;
    const TEXTOS = {
      desligado: ["Microfone desligado", "Clique para ligar"],
      aguardando: ["Aguardando “Jarvis”", "Diga Jarvis e o comando. Clique para desligar"],
      ouvindo: ["Ouvindo o comando…", "Clique para desligar"],
      processando: ["Processando…", "Clique para desligar"],
      falando: ["Jarvis falando…", "Clique para desligar"],
    };
    let estado = "desligado", disponivel = false, dentro = false;
    const api = () => (window.pywebview && window.pywebview.api) || null;

    function mostrar(novo) {
      estado = TEXTOS[novo] ? novo : "desligado";
      const [titulo, dica] = TEXTOS[estado];
      botao.dataset.estado = estado;
      botao.setAttribute("aria-pressed", String(estado !== "desligado"));
      botao.setAttribute("aria-label", `${titulo}. ${dica}`);
      botao.title = dica;
      rotulo.textContent = disponivel ? titulo : "Voz indisponível neste PC";
      botao.disabled = agora.disabled = !disponivel;
    }
    function aplicar(info) {
      if (!info) return;
      disponivel = !!info.disponivel;
      mostrar(info.pausada ? "desligado" : info.estado);
    }
    async function chamar(nome, ...args) {
      try { if (api()) aplicar(await api()[nome](...args)); } catch (e) { /* sem ponte */ }
    }
    // Chamada por results.js (window.onVoice) a cada mudança de estado do microfone.
    function evento(novo) { if (dentro && disponivel) mostrar(novo); }
    function entrar() { dentro = true; mostrar(estado); chamar("escuta_foco", true); }
    function sair() { dentro = false; chamar("escuta_foco", false); }
    function falarAgora() { try { if (disponivel && api()) api().listen_now(); } catch (e) { /* sem ponte */ } }

    botao.addEventListener("click", () => chamar("escuta_definir", estado === "desligado"));
    agora.addEventListener("click", falarAgora);
    document.addEventListener("keydown", (ev) => {
      if (!dentro || ev.code !== "Space" || ev.repeat || ev.ctrlKey || ev.altKey || ev.metaKey) return;
      const a = ev.target;
      if (a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable)) return;
      if (document.querySelector("dialog[open]")) return;
      ev.preventDefault(); falarAgora();
    });
    mostrar("desligado");
    return { entrar, sair, evento, estado: () => estado };
  })();

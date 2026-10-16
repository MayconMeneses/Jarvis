"use strict";
// App da Jarvis no celular: pareia com o PC, conversa e (se o aparelho deixar) fala e escuta em português.
(() => {
  const $ = (id) => document.getElementById(id);
  const CHAVE = "jarvis-token";
  const guardar = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* modo privado */ } };
  const ler = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  let token = ler(CHAVE);

  async function api(caminho, corpo) {
    const resposta = await fetch(caminho, {
      method: corpo ? "POST" : "GET",
      headers: Object.assign({ "Content-Type": "application/json" }, token ? { Authorization: "Bearer " + token } : {}),
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    const dados = await resposta.json().catch(() => ({}));
    if (resposta.status === 401) { guardar(CHAVE, null); token = null; mostrar("parear"); }
    if (!resposta.ok) throw new Error(dados.erro || "erro " + resposta.status);
    return dados;
  }

  function mostrar(tela) {
    $("parear").hidden = tela !== "parear";
    $("chat").hidden = tela !== "chat";
    $("estado").textContent = tela === "chat" ? "conectada" : "não pareado";
  }

  function adicionar(texto, quem, nota) {
    const bolha = document.createElement("div");
    bolha.className = "msg " + quem;
    bolha.textContent = texto;
    if (nota) { const n = document.createElement("small"); n.textContent = nota; bolha.appendChild(n); }
    $("mensagens").appendChild(bolha);
    $("mensagens").scrollTop = $("mensagens").scrollHeight;
  }

  function falar(texto) {
    if (!$("falar").checked || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const fala = new SpeechSynthesisUtterance(texto.slice(0, 600));
    fala.lang = "pt-BR";
    window.speechSynthesis.speak(fala);
  }

  async function enviar(texto) {
    texto = texto.trim();
    if (!texto) return;
    adicionar(texto, "eu");
    $("texto").value = "";
    $("orb").classList.add("pensando");
    $("enviar").disabled = true;
    try {
      const r = await api("/api/chat", { texto });
      const aviso = r.pendentes ? r.pendentes + " ação(ões) esperando sua aprovação no PC" : "";
      adicionar(r.texto, "jarvis", [r.cerebro, aviso].filter(Boolean).join(" · "));
      falar(r.texto);
    } catch (e) {
      adicionar("Não consegui falar com o PC: " + e.message, "jarvis erro");
    } finally {
      $("orb").classList.remove("pensando");
      $("enviar").disabled = false;
    }
  }

  $("form").addEventListener("submit", (ev) => { ev.preventDefault(); enviar($("texto").value); });
  document.querySelectorAll("#atalhos button").forEach((b) => b.addEventListener("click", () => enviar(b.dataset.texto)));

  $("entrar").addEventListener("click", async () => {
    $("erro-parear").textContent = "";
    try {
      const r = await api("/api/parear", { codigo: $("codigo").value, nome: $("nome").value });
      token = r.token;
      guardar(CHAVE, token);
      iniciar();
    } catch (e) {
      $("erro-parear").textContent = e.message;
    }
  });

  // Ditado (Safari no iPhone aceita webkitSpeechRecognition).
  const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;
  // O Safari só libera o microfone em HTTPS: em http:// o botão some e o app explica como ligar a voz.
  const semVoz = !Reconhecimento || !window.isSecureContext;
  if (semVoz) {
    $("mic").hidden = true;
    if (Reconhecimento) $("falar").parentElement.insertAdjacentHTML("afterend",
      '<p class="voz">🎤 O ditado por voz precisa de HTTPS (veja “Tailscale” no guia do celular). Digitar funciona normalmente.</p>');
  } else $("mic").addEventListener("click", () => {
    const rec = new Reconhecimento();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    $("mic").classList.add("ativo");
    rec.onresult = (ev) => enviar(ev.results[0][0].transcript);
    rec.onend = () => $("mic").classList.remove("ativo");
    rec.onerror = () => $("mic").classList.remove("ativo");
    rec.start();
  });

  async function iniciar() {
    if (!token) return mostrar("parear");
    try {
      const e = await api("/api/estado");
      mostrar("chat");
      if (!$("mensagens").children.length) adicionar("Olá, " + (e.usuario || "tudo bem") + "! Estou aqui no seu PC. Em que posso ajudar?", "jarvis");
    } catch (err) {
      $("estado").textContent = "sem conexão com o PC";
      if (token) mostrar("chat");
    }
  }

  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("/sw.js").catch(() => {});
  iniciar();
})();

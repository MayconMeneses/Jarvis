// Voz do Gemini (TTS) OPCIONAL, com a SUA chave Gemini já cadastrada. Só funciona se o usuário ligar a opção em Cérebro > Voz, com aviso claro:
// o TEXTO a ser falado sai do aparelho para o Google (o áudio do microfone não). A chave vai no cabeçalho x-goog-api-key (nunca na URL, nunca em log).
// CORS do generativelanguage.googleapis.com confirmado por curl (OPTIONS aceita x-goog-api-key). Formato: o modelo devolve áudio em base64, PCM 16 bits
// mono 24 kHz (audio/L16) ou WAV com cabeçalho RIFF; aqui os dois viram Int16Array. NÃO verificado com chave real nesta sessão (ver docs).
export const MODELOS_TTS = ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"];
export const VOZES_GEMINI = ["Kore", "Puck", "Charon", "Zephyr", "Aoede", "Fenrir", "Leda", "Orus"];
export const MAX_TEXTO = 350;  // caracteres por pedido (frase a frase)
const BASE = "https://generativelanguage.googleapis.com/v1beta/models/";
const CACHE_MAX = 24, CACHE_MS = 10 * 60 * 1000, TAXA_PADRAO = 24000;

function bytesDe(base64) {
  const bin = atob(String(base64).replace(/\s+/g, ""));
  const b = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) b[i] = bin.charCodeAt(i);
  return b;
}

// Base64 + tipo do arquivo -> { pcm: Int16Array, taxa }. Aceita PCM cru (taxa em "rate=") e WAV (lê fmt e data). Qualquer outra coisa: erro.
export function decodificarAudio(base64, mime = "") {
  const b = bytesDe(base64), v = new DataView(b.buffer);
  let taxa = Number(/rate=(\d+)/i.exec(mime)?.[1]) || TAXA_PADRAO, ini = 0, fim = b.length;
  if (b.length > 12 && String.fromCharCode(...b.slice(0, 4)) === "RIFF" && String.fromCharCode(...b.slice(8, 12)) === "WAVE") {
    let achou = false, canais = 1, bits = 16, formato = 1;
    for (let p = 12; p + 8 <= b.length;) {
      const id = String.fromCharCode(...b.slice(p, p + 4)), tam = v.getUint32(p + 4, true);
      if (id === "fmt ") { formato = v.getUint16(p + 8, true); canais = v.getUint16(p + 10, true); taxa = v.getUint32(p + 12, true); bits = v.getUint16(p + 22, true); }
      if (id === "data") { ini = p + 8; fim = Math.min(b.length, ini + tam); achou = true; break; }
      p += 8 + tam + (tam % 2);
    }
    if (!achou || formato !== 1 || canais !== 1 || bits !== 16) throw new Error("formato de áudio inesperado");
  }
  const n = Math.floor((fim - ini) / 2), pcm = new Int16Array(n);
  for (let i = 0; i < n; i++) pcm[i] = v.getInt16(ini + 2 * i, true);
  if (!n || !(taxa >= 8000 && taxa <= 48000)) throw new Error("áudio vazio ou com taxa inválida");
  return { pcm, taxa };
}

export function criarGemini({ chave, buscar = (...a) => fetch(...a), agora = () => Date.now(), modelos = MODELOS_TTS, tempoMs = 20000 }) {
  const cache = new Map();
  let bom = null;  // último modelo que respondeu
  const ordem = () => (bom ? [bom, ...modelos.filter((m) => m !== bom)] : modelos);

  async function pedir(modelo, texto, voz, sinal) {
    const r = await buscar(`${BASE}${modelo}:generateContent`, {
      method: "POST", signal: sinal, headers: { "Content-Type": "application/json", "x-goog-api-key": await chave() },
      body: JSON.stringify({ contents: [{ parts: [{ text: texto }] }],
        generationConfig: { responseModalities: ["AUDIO"], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voz } } } } }),
    });
    if (!r.ok) {
      const e = new Error(r.status === 401 || r.status === 403 ? "chave recusada pelo Google" : r.status === 429 ? "limite de uso do Gemini atingido" : r.status === 404 ? "modelo de voz não encontrado" : `HTTP ${r.status}`);
      e.status = r.status;
      throw e;
    }
    const parte = ((await r.json()).candidates?.[0]?.content?.parts || []).find((p) => p.inlineData?.data);
    if (!parte) throw new Error("o Gemini não devolveu áudio");
    return decodificarAudio(parte.inlineData.data, parte.inlineData.mimeType);
  }

  return {
    async disponivel() { return Boolean(await chave()); },
    limparCache() { cache.clear(); },
    // Texto (já normalizado, <= 350 caracteres) -> { pcm, taxa }. Cache curto em memória (10 min, 24 frases): frase repetida não gasta cota.
    async sintetizar(texto, { voz = "Kore" } = {}) {
      texto = String(texto || "").trim();
      if (!texto) throw new Error("texto vazio");
      if (texto.length > MAX_TEXTO) throw new Error("texto longo demais para uma fala");
      const k = `${voz}|${texto}`, hit = cache.get(k);
      if (hit && agora() - hit.t < CACHE_MS) { cache.delete(k); cache.set(k, hit); return hit.audio; }
      if (!(await chave())) throw new Error("sem chave do Gemini");
      const ctl = typeof AbortController === "function" ? new AbortController() : null, prazo = ctl ? setTimeout(() => ctl.abort(), tempoMs) : null;
      try {
        let ultimo = null;
        for (const modelo of ordem()) {
          try {
            const audio = await pedir(modelo, texto, voz, ctl?.signal);
            bom = modelo;
            cache.set(k, { audio, t: agora() });
            while (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value);
            return audio;
          } catch (e) {
            ultimo = e;
            if (e.status !== 404 && e.status !== 400) throw e;  // chave, cota e rede não melhoram trocando de modelo; modelo encerrado sim
          }
        }
        throw ultimo || new Error("nenhum modelo de voz respondeu");
      } catch (e) {
        throw e?.name === "AbortError" ? new Error("o Gemini demorou demais") : e;
      } finally { clearTimeout(prazo); }
    },
  };
}

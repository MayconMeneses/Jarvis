// Cópia criptografada, no mesmo formato do PC (jarvis/backup.py): AES-256-GCM, chave por PBKDF2-HMAC-SHA256.
// Usa só o WebCrypto do navegador; a senha nunca é guardada nem enviada para lugar nenhum.
export const FORMATO = "jarvis-backup-1";
export const ITERACOES = 600000;
export const MIN_SENHA = 8;

const paraB64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)));
const deB64 = (texto) => Uint8Array.from(atob(texto), (c) => c.charCodeAt(0));

async function chave(senha, sal, iteracoes) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(senha), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", salt: sal, iterations: iteracoes, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export async function cifrar(texto, senha, iteracoes = ITERACOES) {
  if ([...senha].length < MIN_SENHA) throw new Error(`use uma senha de pelo menos ${MIN_SENHA} caracteres`);
  const sal = crypto.getRandomValues(new Uint8Array(16)), nonce = crypto.getRandomValues(new Uint8Array(12));
  const dados = await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, await chave(senha, sal, iteracoes), new TextEncoder().encode(texto));
  return JSON.stringify({ formato: FORMATO, kdf: "PBKDF2-SHA256", iteracoes, sal: paraB64(sal), nonce: paraB64(nonce), dados: paraB64(dados) });
}

export function eCifrado(conteudo) {
  try { return JSON.parse(conteudo).formato === FORMATO; } catch { return false; }
}

export async function decifrar(conteudo, senha) {
  let c;
  try { c = JSON.parse(conteudo); } catch { throw new Error("arquivo de cópia inválido"); }
  if (c.formato !== FORMATO || !(c.iteracoes >= 1 && c.iteracoes <= 5000000)) throw new Error("arquivo de cópia inválido");
  try {
    const aberto = await crypto.subtle.decrypt({ name: "AES-GCM", iv: deB64(c.nonce) }, await chave(senha, deB64(c.sal), c.iteracoes), deB64(c.dados));
    return new TextDecoder().decode(aberto);
  } catch { throw new Error("senha incorreta ou arquivo alterado"); }
}

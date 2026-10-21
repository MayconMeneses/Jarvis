// Limite simples por IP (memória do isolate do Worker: melhor esforço, não é contador global). O IP vem de cf-connecting-ip.
const janelas = new Map();

export function dentroDoLimite(ip, maximo, agora = Date.now()) {
  if (janelas.size > 5000) { for (const [k, v] of janelas) if (agora - v.inicio > 60000) janelas.delete(k); if (janelas.size > 5000) janelas.clear(); }
  let j = janelas.get(ip);
  if (!j || agora - j.inicio > 60000) { j = { inicio: agora, n: 0 }; janelas.set(ip, j); }
  j.n += 1;
  return j.n <= maximo;
}
export function zerarLimites() { janelas.clear(); }

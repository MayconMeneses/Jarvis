// Temas por frequência de termos (sem IA), igual a jarvis/instagram/temas.py.
import { fold } from "./util.js";

const STOP = new Set(`para como mais muito pelo pela pelos pelas esse essa esses essas este esta estes estas isso isto aqui ainda
sobre entre quando onde porque qual quais seus suas voce voces nosso nossa depois antes sempre nunca todo toda todos todas
tudo nada algo cada outro outra outros outras fazer feito feita fica ficar vamos pode podem quer quero tem tenho temos
mesmo mesma tambem apenas ate desde sem com por que uma uns umas dos das nos nas num numa seu sua meu minha nao sim
ser foi sao era vai vou ver hoje agora link bio comente comenta salve salva compartilhe siga segue mas pra ele ela`.split(/\s+/));

const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

export function termos(legenda) {
  return (fold(legenda ?? "").replace(/@\w+/g, " ").match(/[a-z0-9]+/g) || []).filter((t) => t.length >= 3 && !/^\d+$/.test(t) && !STOP.has(t));
}

export function mediana(valores) {
  const s = [...valores].sort((a, b) => a - b);
  if (!s.length) return null;
  const meio = Math.floor(s.length / 2);
  return s.length % 2 ? s[meio] : (s[meio - 1] + s[meio]) / 2;
}

export function temasPorFrequencia(itens, maximo = 8, minimoPosts = 2) {
  const uni = new Map(), bi = new Map();
  const somar = (mapa, chave, i) => { if (!mapa.has(chave)) mapa.set(chave, new Set()); mapa.get(chave).add(i); };
  itens.forEach((item, i) => {
    const ts = termos(item.legenda);
    new Set(ts).forEach((t) => somar(uni, t, i));
    for (let k = 0; k + 1 < ts.length; k++) somar(bi, `${ts[k]} ${ts[k + 1]}`, i);
  });
  const ordenar = (mapa) => [...mapa].filter(([, p]) => p.size >= minimoPosts).sort((a, b) => b[1].size - a[1].size || cmp(a[0], b[0]));
  const escolhidos = [];
  for (const [rotulo, posts] of [...ordenar(bi), ...ordenar(uni)]) {
    if (escolhidos.some(([e]) => e.includes(rotulo) || (!rotulo.includes(" ") && e.split(" ").includes(rotulo)))) continue;
    escolhidos.push([rotulo, posts]);
    if (escolhidos.length === maximo) break;
  }
  return escolhidos.map(([rotulo, posts]) => {
    const membros = [...posts].sort((a, b) => a - b).map((i) => itens[i]);
    return { rotulo, posts: membros.length, alcance_mediano: mediana(membros.filter((m) => m.razao_alcance != null).map((m) => m.razao_alcance)),
      perfis: [...new Set(membros.map((m) => m.perfil))].sort(cmp), proprio: membros.some((m) => m.proprio) };
  }).sort((a, b) => (a.alcance_mediano == null) - (b.alcance_mediano == null) || (b.alcance_mediano ?? 0) - (a.alcance_mediano ?? 0) || b.posts - a.posts || cmp(a.rotulo, b.rotulo));
}

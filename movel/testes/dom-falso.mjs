// DOM mínimo para testar as caixas e painéis no node (sem jsdom): só o que o app usa. Não é um teste (o nome não termina em .test.mjs).
export class No {
  constructor(tag) { Object.assign(this, { tag, filhos: [], atributos: {}, dataset: {}, ouvintes: {}, _texto: "", hidden: false, disabled: false }); }
  get textContent() { return this._texto + this.filhos.map((f) => f.textContent).join(""); }
  set textContent(v) { this._texto = String(v); this.filhos = []; }
  append(...nos) { for (const n of nos) this.filhos.push(typeof n === "string" ? Object.assign(new No("#texto"), { _texto: n }) : n); }
  appendChild(n) { this.append(n); return n; }
  replaceChildren(...nos) { this.filhos = []; this._texto = ""; this.append(...nos); }
  setAttribute(k, v) { this.atributos[k] = String(v); }
  getAttribute(k) { return this.atributos[k] ?? null; }
  addEventListener(t, f) { (this.ouvintes[t] ||= []).push(f); }
  async clicar() { for (const f of this.ouvintes.click || []) await f({ target: this }); }
}

export function instalarDom() {
  globalThis.document = { hidden: false, createElement: (tag) => new No(tag), addEventListener() {}, removeEventListener() {}, getElementById: () => null };
  return globalThis.document;
}

// Todos os nós (em profundidade) que satisfazem `pred`.
export function achar(raiz, pred, saida = []) {
  if (pred(raiz)) saida.push(raiz);
  raiz.filhos.forEach((f) => achar(f, pred, saida));
  return saida;
}

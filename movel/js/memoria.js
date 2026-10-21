// Memória própria do celular: notas, diário e configurações, só neste aparelho (IndexedDB).
// O "armazenamento" é trocável: no navegador usa IndexedDB; nos testes, um Map em memória.
import { fold, isoData } from "./util.js";
import { lerCopia } from "./restaurar.js";

export class ArmazemMemoria {
  constructor() { this.dados = new Map(); }
  async ler(chave) { return this.dados.has(chave) ? structuredClone(this.dados.get(chave)) : undefined; }
  async gravar(chave, valor) { this.dados.set(chave, structuredClone(valor)); }
  async apagar(chave) { this.dados.delete(chave); }
  async chaves() { return [...this.dados.keys()]; }
}

export class ArmazemIndexedDB {
  constructor(nome = "jarvis-movel") { this.nome = nome; this._db = null; }
  _abrir() {
    this._db ||= new Promise((resolver, rejeitar) => {
      const pedido = indexedDB.open(this.nome, 1);
      pedido.onupgradeneeded = () => pedido.result.createObjectStore("kv");
      pedido.onsuccess = () => resolver(pedido.result);
      pedido.onerror = () => rejeitar(pedido.error);
    });
    return this._db;
  }
  async _tx(modo, fn) {
    const db = await this._abrir();
    return new Promise((resolver, rejeitar) => {
      const req = fn(db.transaction("kv", modo).objectStore("kv"));
      req.onsuccess = () => resolver(req.result);
      req.onerror = () => rejeitar(req.error);
    });
  }
  ler(chave) { return this._tx("readonly", (s) => s.get(chave)); }
  gravar(chave, valor) { return this._tx("readwrite", (s) => s.put(valor, chave)); }
  apagar(chave) { return this._tx("readwrite", (s) => s.delete(chave)); }
  chaves() { return this._tx("readonly", (s) => s.getAllKeys()); }
}

const NOTA = "nota:";
const META = "meta:";

export class Memoria {
  constructor(armazem = new ArmazemMemoria(), relogio = () => new Date()) { this.armazem = armazem; this.relogio = relogio; }

  async guardar(ref, corpo, tipo = "nota", titulo = "") {
    ref = String(ref).trim().replace(/\s+/g, " ").slice(0, 120);
    if (!ref) throw new Error("informe um nome para a nota");
    const antiga = await this.armazem.ler(NOTA + ref);
    const agora = this.relogio().toISOString();
    const nota = { ref, titulo: titulo || ref.split("/").pop(), tipo, corpo: String(corpo).slice(0, 20000), criada: antiga?.criada || agora, atualizada: agora };
    await this.armazem.gravar(NOTA + ref, nota);
    return nota;
  }

  async ler(ref) { return (await this.armazem.ler(NOTA + ref)) || null; }
  async apagar(ref) { await this.armazem.apagar(NOTA + ref); }

  async listar(prefixo = "") {
    const chaves = (await this.armazem.chaves()).filter((c) => c.startsWith(NOTA + prefixo));
    const notas = await Promise.all(chaves.map((c) => this.armazem.ler(c)));
    return notas.sort((a, b) => b.atualizada.localeCompare(a.atualizada));
  }

  // Busca simples por palavras (sem acento): título pesa mais que o corpo.
  async buscar(consulta, limite = 5) {
    const termos = fold(consulta).split(/\W+/).filter((t) => t.length > 2);
    if (!termos.length) return [];
    const pontuadas = [];
    for (const nota of await this.listar()) {
      const titulo = fold(nota.titulo + " " + nota.ref), corpo = fold(nota.corpo);
      const pontos = termos.reduce((p, t) => p + (titulo.includes(t) ? 5 : 0) + (corpo.includes(t) ? 1 : 0), 0);
      if (pontos) pontuadas.push([pontos, nota]);
    }
    return pontuadas.sort((a, b) => b[0] - a[0]).slice(0, limite).map(([, n]) => n);
  }

  async diario(texto) {
    const hoje = this.relogio();
    const ref = `Diário/${isoData(hoje)}`;  // data LOCAL (às 21h no Brasil o dia em UTC já seria o seguinte)
    const atual = (await this.ler(ref))?.corpo || "";
    const hora = hoje.toTimeString().slice(0, 5);
    await this.guardar(ref, `${atual}${atual ? "\n" : ""}- ${hora} — ${String(texto).replace(/\n/g, " ").slice(0, 300)}`, "diario");
  }

  async meta(chave) { return this.armazem.ler(META + chave); }
  async definirMeta(chave, valor) { await this.armazem.gravar(META + chave, valor); }

  // Cópia de segurança: um arquivo JSON que o usuário guarda onde quiser (nada sai do aparelho sozinho).
  async exportar() {
    const notas = await this.listar();
    const meta = {};
    for (const c of (await this.armazem.chaves()).filter((k) => k.startsWith(META))) meta[c.slice(META.length)] = await this.armazem.ler(c);
    return JSON.stringify({ formato: "jarvis-movel-1", exportado: this.relogio().toISOString(), notas, meta }, null, 1);
  }

  // Restaura só o que passa na validação (ver restaurar.js). Devolve o relatório; `importar` devolve só a contagem de notas.
  async restaurar(texto) {
    const r = lerCopia(texto);
    for (const n of r.notas) await this.armazem.gravar(NOTA + n.ref, n);
    for (const [k, v] of Object.entries(r.meta)) await this.armazem.gravar(META + k, v);
    return r;
  }

  async importar(texto) { return (await this.restaurar(texto)).notas.length; }
}

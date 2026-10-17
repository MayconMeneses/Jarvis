// Arquivos da Oficina no celular: cada arquivo é uma nota "Oficina/<projeto>/<caminho>" (entra na cópia de segurança e aparece na
// aba Memória) e cada gravação guarda a versão anterior (últimas 20) para desfazer. Mesmas regras de nome do PC.
const PERMITIDAS = new Set([".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md", ".txt", ".toml", ".yml", ".yaml", ".sql", ".go", ".java", ".cs", ".ini", ".cfg"]);
export const MAX_ARQUIVOS = 60, MAX_CHARS = 20000, MAX_VERSOES = 20;
const PROJETO = /^[\p{L}\p{N}_][\p{L}\p{N}_ -]{0,39}$/u;
const SEGMENTO = /^[\p{L}\p{N}_][\p{L}\p{N}_.-]*$/u;
const VERSOES = "ofv:";

export function caminhoSeguro(caminho) {
  const texto = String(caminho).trim().replace(/\\/g, "/");
  const partes = texto.split("/");
  if (!texto || texto.startsWith("/") || /^[A-Za-z]:/.test(texto) || partes.length > 4) throw new Error(`caminho não permitido: ${caminho}`);
  const gitignore = texto === ".gitignore";  // o único arquivo com ponto no começo que os modelos usam
  if (!gitignore && partes.some((p) => p === ".." || p === "." || !SEGMENTO.test(p))) throw new Error(`caminho não permitido: ${caminho}`);
  const ext = (/\.[^./]+$/.exec(partes.at(-1)) || [""])[0].toLowerCase();
  if (!gitignore && !PERMITIDAS.has(ext)) throw new Error(`tipo de arquivo não permitido: ${caminho}`);
  return partes.join("/");
}

export class EspacoOficina {
  constructor(memoria) { this.memoria = memoria; this.armazem = memoria.armazem; }

  _projeto(nome) {
    if (!PROJETO.test(String(nome))) throw new Error("nome de projeto inválido (letras, números, espaço e hífen; até 40 caracteres)");
    return String(nome);
  }

  async projetos() {
    const lista = (await this.memoria.meta("oficina:projetos")) || [];
    const dosArquivos = (await this.memoria.listar("Oficina/")).map((n) => n.ref.split("/")[1]);
    return [...new Set([...lista, ...dosArquivos])].sort();
  }

  async criar(nome) {
    this._projeto(nome);
    const lista = new Set((await this.memoria.meta("oficina:projetos")) || []);
    lista.add(nome);
    await this.memoria.definirMeta("oficina:projetos", [...lista]);
    return nome;
  }

  async arquivos(projeto) {
    this._projeto(projeto);
    const notas = (await this.memoria.listar(`Oficina/${projeto}/`)).slice(0, MAX_ARQUIVOS);
    return Object.fromEntries(notas.map((n) => [n.ref.slice(`Oficina/${projeto}/`.length), n.corpo]).sort());
  }

  async _guardarVersao(ref, texto) {
    const versoes = (await this.armazem.ler(VERSOES + ref)) || [];
    versoes.push(texto);
    await this.armazem.gravar(VERSOES + ref, versoes.slice(-MAX_VERSOES));
  }

  async salvar(projeto, caminho, conteudo) {
    this._projeto(projeto);
    const nome = caminhoSeguro(caminho), ref = `Oficina/${projeto}/${nome}`;
    if (String(conteudo).length > MAX_CHARS) throw new Error(`arquivo grande demais (máximo ${MAX_CHARS} caracteres)`);
    const atual = await this.memoria.ler(ref);
    if (!atual && Object.keys(await this.arquivos(projeto)).length >= MAX_ARQUIVOS) throw new Error(`projeto com arquivos demais (máximo ${MAX_ARQUIVOS})`);
    if (atual) {
      if (atual.corpo === conteudo) return nome;
      await this._guardarVersao(ref, atual.corpo);
    }
    await this.memoria.guardar(ref, conteudo, "codigo", nome);
    await this.criar(projeto);
    return nome;
  }

  async apagar(projeto, caminho) {
    this._projeto(projeto);
    const nome = caminhoSeguro(caminho), ref = `Oficina/${projeto}/${nome}`, atual = await this.memoria.ler(ref);
    if (!atual) return false;
    await this._guardarVersao(ref, atual.corpo);
    await this.memoria.apagar(ref);
    return true;
  }

  async versoes(projeto, caminho) { return ((await this.armazem.ler(VERSOES + `Oficina/${this._projeto(projeto)}/${caminhoSeguro(caminho)}`)) || []).length; }

  // Volta para a versão anterior; a atual vira uma versão, então desfazer de novo refaz.
  async desfazer(projeto, caminho) {
    this._projeto(projeto);
    const nome = caminhoSeguro(caminho), ref = `Oficina/${projeto}/${nome}`;
    const versoes = (await this.armazem.ler(VERSOES + ref)) || [];
    if (!versoes.length) throw new Error("não há versão anterior deste arquivo");
    const anterior = versoes.pop();
    const atual = await this.memoria.ler(ref);
    if (atual) versoes.push(atual.corpo);
    await this.armazem.gravar(VERSOES + ref, versoes.slice(-MAX_VERSOES));
    await this.memoria.guardar(ref, anterior, "codigo", nome);
    return anterior;
  }
}

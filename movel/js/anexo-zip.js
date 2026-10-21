// Leitor de ZIP mínimo e DEFENSIVO (a base de .docx, .xlsx e .pptx). Sem bibliotecas: usa o DecompressionStream do navegador.
// Nunca grava nada em disco, mas mesmo assim recusa: nomes com "../" ou caminho absoluto, entradas cifradas, "bomba de zip"
// (razão de compressão absurda ou tamanho real maior que o declarado) e arquivos com entradas demais.
import { crc32 } from "./zip.js";

export const LIMITES_ZIP = { entradas: 2000, porEntrada: 20 * 1024 * 1024, total: 60 * 1024 * 1024, razao: 150 };

export class ZipInvalido extends Error {}

const u16 = (v, o) => v.getUint16(o, true);
const u32 = (v, o) => v.getUint32(o, true);

export const nomeSeguro = (nome) => Boolean(nome) && !nome.includes("\0") && !/^([/\\]|[A-Za-z]:)/.test(nome) && !nome.split(/[/\\]/).includes("..");

function acharFim(v, bytes) {
  const minimo = Math.max(0, bytes.length - 22 - 65535);
  for (let i = bytes.length - 22; i >= minimo; i--) if (u32(v, i) === 0x06054b50) return i;
  throw new ZipInvalido("não é um arquivo ZIP válido (fim do índice não encontrado)");
}

function lerIndice(bytes, limites) {
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const fim = acharFim(v, bytes);
  const quantas = u16(v, fim + 10), inicio = u32(v, fim + 16);
  if (quantas > limites.entradas) throw new ZipInvalido(`o arquivo tem entradas demais (${quantas}; limite ${limites.entradas})`);
  const entradas = new Map(), ignoradas = [];
  let pos = inicio;
  for (let i = 0; i < quantas; i++) {
    if (pos + 46 > bytes.length || u32(v, pos) !== 0x02014b50) throw new ZipInvalido("índice do ZIP corrompido");
    const nLen = u16(v, pos + 28), eLen = u16(v, pos + 30), cLen = u16(v, pos + 32);
    if (pos + 46 + nLen > bytes.length) throw new ZipInvalido("índice do ZIP corrompido");
    const nome = new TextDecoder("utf-8").decode(bytes.subarray(pos + 46, pos + 46 + nLen));
    const e = { nome, flags: u16(v, pos + 8), metodo: u16(v, pos + 10), crc: u32(v, pos + 16), comprimido: u32(v, pos + 20), tamanho: u32(v, pos + 24), local: u32(v, pos + 42) };
    if (!nomeSeguro(nome)) ignoradas.push(nome); else if (!nome.endsWith("/")) entradas.set(nome, e);
    pos += 46 + nLen + eLen + cLen;
  }
  return { v, entradas, ignoradas };
}

async function inflar(dados, maximo) {
  const ds = new DecompressionStream("deflate-raw");
  const escritor = ds.writable.getWriter();
  const escrita = escritor.write(dados).then(() => escritor.close()).catch(() => {});
  const leitor = ds.readable.getReader();
  const partes = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await leitor.read();
      if (done) break;
      total += value.length;
      if (total > maximo) { await leitor.cancel().catch(() => {}); throw new ZipInvalido("conteúdo descompactado maior que o permitido (possível bomba de ZIP)"); }
      partes.push(value);
    }
  } catch (e) {
    if (e instanceof ZipInvalido) throw e;
    throw new ZipInvalido("dados comprimidos corrompidos");
  }
  await escrita;
  const saida = new Uint8Array(total);
  let p = 0;
  for (const parte of partes) { saida.set(parte, p); p += parte.length; }
  return saida;
}

export function abrirZip(bytes, limites = LIMITES_ZIP) {
  const { v, entradas, ignoradas } = lerIndice(bytes, limites);
  let lidoTotal = 0;
  return {
    ignoradas,
    nomes: () => [...entradas.keys()],
    tem: (nome) => entradas.has(nome),
    async ler(nome) {
      const e = entradas.get(nome);
      if (!e) return null;
      if (e.flags & 1) throw new ZipInvalido("o arquivo está protegido por senha");
      if (e.tamanho > limites.porEntrada) throw new ZipInvalido(`"${nome}" é grande demais (${Math.round(e.tamanho / 1048576)} MB)`);
      if (e.tamanho > 1048576 && e.tamanho / Math.max(1, e.comprimido) > limites.razao) throw new ZipInvalido("razão de compressão suspeita (possível bomba de ZIP)");
      if (lidoTotal + e.tamanho > limites.total) throw new ZipInvalido("o conteúdo total do arquivo é grande demais");
      if (e.local + 30 > bytes.length || u32(v, e.local) !== 0x04034b50) throw new ZipInvalido("entrada do ZIP corrompida");
      const ini = e.local + 30 + u16(v, e.local + 26) + u16(v, e.local + 28);
      if (ini + e.comprimido > bytes.length) throw new ZipInvalido("entrada do ZIP truncada");
      const cru = bytes.subarray(ini, ini + e.comprimido);
      let dados;
      if (e.metodo === 0) dados = cru;
      else if (e.metodo === 8) dados = await inflar(cru, Math.min(limites.porEntrada, e.tamanho + 16));
      else throw new ZipInvalido(`método de compressão ${e.metodo} não suportado`);
      if (dados.length !== e.tamanho) throw new ZipInvalido(`"${nome}" não confere com o tamanho declarado`);
      if (crc32(dados) !== e.crc) throw new ZipInvalido(`"${nome}" está corrompido (CRC)`);
      lidoTotal += dados.length;
      return dados;
    },
    async texto(nome) { const d = await this.ler(nome); return d && new TextDecoder("utf-8").decode(d); },
  };
}

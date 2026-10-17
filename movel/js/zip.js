// ZIP sem compressão (método "store"), em JavaScript puro: para baixar um projeto inteiro no celular. Nomes em UTF-8.
const TABELA = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
  return t;
})();

export function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = TABELA[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dataDos(d) {
  return [((d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1)) & 0xffff, (((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()) & 0xffff];
}

// arquivos: { "pasta/arquivo.py": "texto" } -> Uint8Array do .zip
export function zip(arquivos, agora = new Date()) {
  const enc = new TextEncoder();
  const [hora, data] = dataDos(agora);
  const partes = [], central = [];
  let deslocamento = 0;
  for (const [nome, texto] of Object.entries(arquivos)) {
    const n = enc.encode(nome), corpo = enc.encode(texto), crc = crc32(corpo);
    const local = new DataView(new ArrayBuffer(30));
    [[0, 0x04034b50, 4], [4, 20, 2], [6, 0x0800, 2], [8, 0, 2], [10, hora, 2], [12, data, 2], [14, crc, 4], [18, corpo.length, 4], [22, corpo.length, 4], [26, n.length, 2], [28, 0, 2]]
      .forEach(([o, v, t]) => (t === 4 ? local.setUint32(o, v, true) : local.setUint16(o, v, true)));
    partes.push(new Uint8Array(local.buffer), n, corpo);
    const dir = new DataView(new ArrayBuffer(46));
    [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [8, 0x0800, 2], [10, 0, 2], [12, hora, 2], [14, data, 2], [16, crc, 4], [20, corpo.length, 4], [24, corpo.length, 4],
      [28, n.length, 2], [30, 0, 2], [32, 0, 2], [34, 0, 2], [36, 0, 2], [38, 0, 4], [42, deslocamento, 4]].forEach(([o, v, t]) => (t === 4 ? dir.setUint32(o, v, true) : dir.setUint16(o, v, true)));
    central.push(new Uint8Array(dir.buffer), n);
    deslocamento += 30 + n.length + corpo.length;
  }
  const tamanhoCentral = central.reduce((s, p) => s + p.length, 0);
  const fim = new DataView(new ArrayBuffer(22));
  fim.setUint32(0, 0x06054b50, true);
  fim.setUint16(8, Object.keys(arquivos).length, true);
  fim.setUint16(10, Object.keys(arquivos).length, true);
  fim.setUint32(12, tamanhoCentral, true);
  fim.setUint32(16, deslocamento, true);
  const total = deslocamento + tamanhoCentral + 22;
  const saida = new Uint8Array(total);
  let pos = 0;
  for (const p of [...partes, ...central, new Uint8Array(fim.buffer)]) { saida.set(p, pos); pos += p.length; }
  return saida;
}

// Ajudante dos testes de anexos/documentos: um "File" falso com os bytes dados.
export const arquivo = (name, dados, type = "") => {
  const b = Buffer.from(dados);
  return { name, type, size: b.length, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) };
};

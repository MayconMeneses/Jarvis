// Utilidades comuns: texto sem acento, datas e limites.
export const fold = (texto) => String(texto).toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");

export const escaparRegex = (texto) => texto.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export const cortar = (texto, limite) => (texto.length <= limite ? texto : texto.slice(0, limite).replace(/\s+\S*$/, "") + "…");

export const dois = (n) => String(n).padStart(2, "0");

export const isoData = (data) => `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}`;

// Semana ISO (segunda-feira como início), igual ao isocalendar() do Python.
export function semanaIso(data) {
  const d = new Date(Date.UTC(data.getFullYear(), data.getMonth(), data.getDate()));
  const dia = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dia);
  const inicioAno = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return [d.getUTCFullYear(), Math.ceil(((d - inicioAno) / 86400000 + 1) / 7)];
}

export const DIAS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];
export const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

export const dataPorExtenso = (d) => `${DIAS[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;

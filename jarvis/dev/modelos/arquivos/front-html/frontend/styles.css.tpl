:root {
  --fundo: #f6f7f9; --cartao: #ffffff; --texto: #1c2430; --suave: #6b7686; --borda: #d9dee6;
  --acento: #2563eb; --erro: #b42318;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root { --fundo: #11161d; --cartao: #1a212b; --texto: #e8edf3; --suave: #93a0b1; --borda: #2b3442; --acento: #5b8def; --erro: #ff8a80; }
}
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.5 system-ui, "Segoe UI", sans-serif; color: var(--texto); background: var(--fundo); }
main { max-width: 560px; margin: 0 auto; padding: 32px 16px; }
h1 { margin: 0 0 20px; font-size: 1.6rem; }
form { display: flex; gap: 8px; }
input { flex: 1; min-width: 0; padding: 10px 12px; font: inherit; color: inherit; background: var(--cartao); border: 1px solid var(--borda); border-radius: 8px; }
input[type="checkbox"] { flex: none; width: 18px; height: 18px; padding: 0; accent-color: var(--acento); }
button { padding: 10px 14px; font: inherit; color: #fff; background: var(--acento); border: 0; border-radius: 8px; cursor: pointer; }
button:focus-visible, input:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }
ul { margin: 20px 0 0; padding: 0; list-style: none; display: grid; gap: 8px; }
li { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--cartao); border: 1px solid var(--borda); border-radius: 8px; }
li span { flex: 1; overflow-wrap: anywhere; }
li.feito span { color: var(--suave); text-decoration: line-through; }
li button { padding: 4px 10px; color: var(--erro); background: transparent; border: 1px solid var(--borda); }
#aviso, .erro { min-height: 1.5em; margin: 10px 0 0; color: var(--erro); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

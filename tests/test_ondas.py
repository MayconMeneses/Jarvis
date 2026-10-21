"""Ondas de áudio laterais, orbe pequeno de escuta e aviso de rede do celular (janela principal)."""

import json
import re
import shutil
import subprocess

import pytest

from jarvis.ui import web

JS = web.BASE / "js"
precisa_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node não instalado")


def _node(codigo: str):
    saida = subprocess.run(["node", "-e", codigo], capture_output=True, text=True, encoding="utf-8", timeout=30, check=True).stdout
    return json.loads(saida)


def _ondas(expressao: str):
    caminho = json.dumps((JS / "ondas.js").as_posix())
    return _node(f"const M = require({caminho}); console.log(JSON.stringify({expressao}));")


@precisa_node
def test_canais_entrada_so_ouvindo_com_mic_fresco_e_saida_so_falando():
    base = "{estado:'%s', mic:0.7, micT:1000, nivel:0.4}"
    assert _ondas("M.canais(%s, 1200)" % (base % "listening")) == {"entrada": 0.7, "saida": 0}
    assert _ondas("M.canais(%s, 1700)" % (base % "listening")) == {"entrada": 0, "saida": 0}  # mic velho (> 500 ms) = silêncio
    assert _ondas("M.canais(%s, 1200)" % (base % "speaking")) == {"entrada": 0, "saida": 0.4}
    assert _ondas("M.canais(%s, 1200)" % (base % "idle")) == {"entrada": 0, "saida": 0}
    assert _ondas("M.canais(%s, 1200)" % (base % "thinking")) == {"entrada": 0, "saida": 0}


@precisa_node
def test_anel_de_60_amostras_guarda_as_mais_novas_e_limita_0_a_1():
    r = _ondas("""(() => { const b = new Float32Array(M.N); let c = 0;
      for (let i = 0; i < 70; i++) c = M.empurrar(b, c, i === 69 ? 5 : i / 100);
      return { n: M.N, nova: M.amostra(b, c, 0), anterior: M.amostra(b, c, 1), velha: M.amostra(b, c, 59), cabeca: c,
               lixo: (() => { const x = new Float32Array(4); M.empurrar(x, 0, NaN); M.empurrar(x, 1, -3); return [x[0], x[1]]; })() }; })()""")
    assert r["n"] == 60 and r["nova"] == 1  # 5 vira 1 (limite)
    assert abs(r["anterior"] - 0.68) < 1e-6 and abs(r["velha"] - 0.10) < 1e-6  # só as últimas 60 de 70 ficam: i = 10..69
    assert r["cabeca"] == 10 and r["lixo"] == [0, 0]  # NaN e negativo viram 0


@precisa_node
def test_silencio_e_reto_e_zerado_detecta_historico_vazio():
    r = _ondas("({z: M.zerado(new Float32Array(60)), v: M.zerado(Float32Array.from([0, 0.5])), f: [0, 1, 7, 59].map(M.forma)})")
    assert r["z"] is True and r["v"] is False
    assert all(0.4 < x < 1.01 for x in r["f"])  # a textura nunca zera nem estoura o painel; o nível é quem multiplica


def test_pagina_tem_ondas_laterais_e_orbe_pequeno_acessivel():
    html = (web.BASE / "index.html").read_text(encoding="utf-8")
    for ident in ("onda-entrada", "onda-saida", "escuta", "escuta-anel", "escuta-linha"):
        assert f'id="{ident}"' in html
    botao = re.search(r'<button[^>]*id="escuta"[^>]*>', html).group(0)
    assert 'aria-label="Falar com a Jarvis"' in botao and 'aria-pressed="false"' in botao and 'type="button"' in botao
    assert 'id="escuta-anel" aria-hidden="true"' in html  # o desenho é decoração; o botão é quem fala com o leitor de tela
    assert html.count('class="onda-painel" aria-hidden="true"') == 2


def test_ondas_entram_na_pagina_montada_depois_do_orbe_e_antes_de_results():
    js, css = web.JS, web.CSS
    assert js.index("orbe") < js.index("ondas") < js.index("results") and "ondas" in css
    pagina = web.page()
    assert "window.Ondas" in pagina and ".onda-painel" in pagina


def test_laco_das_ondas_e_leve_sem_innerhtml_cor_fixa_e_com_pausa():
    cor_fixa = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d")
    js = (JS / "ondas.js").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", (web.BASE / "css" / "ondas.css").read_text(encoding="utf-8"), flags=re.S)
    assert not cor_fixa.search(js) and not cor_fixa.search(css)
    assert "innerHTML" not in js and "eval(" not in js and "shadowBlur" not in js and "backdrop-filter" not in css
    assert ">= 48" in js  # <= ~20 quadros por segundo
    for pausa in ("document.hidden", "IntersectionObserver", "desligado", "visibilitychange"):
        assert pausa in js
    assert "prefers-reduced-motion" in css


def test_orbe_grande_expoe_roda_para_o_laco_das_ondas():
    assert "roda: () => !!raf" in (JS / "orbe.js").read_text(encoding="utf-8")
    assert "definirDisponivel" in (JS / "main.js").read_text(encoding="utf-8")


# ── aviso de rede do celular (campo opcional vindo da ponte) ────────────────────────────────────────

@precisa_node
@pytest.mark.parametrize(("entrada", "texto", "oculto"), [
    ("Wi-Fi público: use o Tailscale.", "Wi-Fi público: use o Tailscale.", False),
    ("  muito\n   espaço  ", "muito espaço", False),
    (None, "", True),  # campo ausente (versão antiga da ponte)
    ("", "", True),
    (42, "", True),
    ("<b>x</b>", "<b>x</b>", False),  # vira texto puro (textContent), nunca HTML
])
def test_aviso_de_rede_do_celular_e_tolerante_e_so_texto(entrada, texto, oculto):
    caminho = json.dumps((JS / "mobile.js").as_posix())
    r = _node(f"""
      const fs = require('fs'), vm = require('vm');
      const el = {{ textContent: 'antigo', hidden: true, addEventListener() {{}}, replaceChildren() {{}}, appendChild() {{}} }};
      const ctx = {{ document: {{ getElementById: () => el }}, window: {{ pywebview: {{ api: {{}} }} }} }};
      vm.createContext(ctx); vm.runInContext(fs.readFileSync({caminho}, 'utf-8') + '\\nthis.mostrar = mostrarAviso;', ctx);
      ctx.mostrar({json.dumps(entrada)}); console.log(JSON.stringify({{ t: el.textContent, h: el.hidden }}));""")
    assert r == {"t": texto, "h": oculto}


def test_aviso_de_rede_fica_no_dialogo_do_celular_discreto_e_sem_innerhtml():
    brains = (web.BASE / "brains.html").read_text(encoding="utf-8")
    assert re.search(r'<p class="aviso-rede" id="mobile-aviso" role="note" hidden>', brains)
    assert brains.index('id="mobile-code"') < brains.index('id="mobile-aviso"') < brains.index('id="mobile-devices"')
    mobile = (JS / "mobile.js").read_text(encoding="utf-8")
    assert "aviso_rede" in mobile and "innerHTML" not in mobile
    assert "var(--" in (web.BASE / "css" / "brains.css").read_text(encoding="utf-8").split(".aviso-rede")[1].split("}")[0]

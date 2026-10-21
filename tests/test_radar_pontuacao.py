import pytest

from jarvis.radar import curadoria, dedup, pontuacao
from jarvis.radar.historico import Historico
from jarvis.radar.modelos import Artigo, Fonte, Item

AGORA = 1_792_500_000.0
HORA = 3600


def art(titulo="Titulo", fonte="A", horas=1.0, nota=5.0, resumo="", link=None):
    return Artigo(fonte, titulo, link or f"https://{fonte.lower()}.com/{abs(hash(titulo)) % 9999}", AGORA - horas * HORA, resumo,
                  nota_fonte=nota)


# ── deduplicação ─────────────────────────────────────────────────────────

def test_url_normalization_removes_tracking_and_decorations():
    base = "https://exemplo.com/noticia/1"
    for variante in ("http://www.exemplo.com/noticia/1/", "https://exemplo.com/noticia/1?utm_source=x&fbclid=abc#topo",
                     "https://EXEMPLO.com/noticia/1/amp"):
        assert dedup.normalizar_url(variante) == dedup.normalizar_url(base)
    assert dedup.normalizar_url("https://exemplo.com/n?id=2") != dedup.normalizar_url("https://exemplo.com/n?id=3")


def test_same_story_in_four_outlets_appears_once_with_also_in():
    titulo = "Banco Central aprova nova regra para o Pix"
    artigos = [art(titulo, "G1", nota=8), art(titulo + " nesta terça", "Folha", nota=7),
               art("BC aprova nova regra para o Pix", "Estadão", nota=6), art(titulo, "G1", nota=8, link="https://g1.com/outro"),
               art("Time vence o campeonato estadual", "UOL", nota=5)]
    grupos = dedup.agrupar(artigos)
    assert len(grupos) == 2
    principal, outros = grupos[0]
    assert principal.fonte == "G1" and sorted(outros) == ["Estadão", "Folha"]  # G1 repetido não vira "também em"


def test_title_similarity_threshold():
    assert dedup.parecidos("Governo anuncia novo pacote de medidas", "Governo anuncia novo pacote de medidas hoje")
    assert not dedup.parecidos("Governo anuncia novo pacote", "Time vence o campeonato")
    assert not dedup.parecidos("", "qualquer coisa")


# ── histórico ────────────────────────────────────────────────────────────

@pytest.fixture
def hist(tmp_path):
    h = Historico(tmp_path / "radar.db")
    yield h
    h.fechar()


def test_second_run_does_not_repeat_anything(hist):
    artigos = [art("Primeira notícia importante"), art("Segunda notícia relevante", "B")]
    assert hist.registrar(artigos, agora=AGORA) == 2
    assert all(hist.ja_visto(a) for a in artigos)
    assert hist.registrar(artigos, agora=AGORA) == 0  # nada novo na segunda rodada


def test_search_cleanup_and_recent_titles(hist):
    velho, novo = art("Reforma tributária avança no Senado"), art("Chuva forte atinge a capital")
    hist.registrar([velho], agora=AGORA - 100 * 86400)
    hist.registrar([novo], agora=AGORA)
    assert [r["titulo"] for r in hist.buscar("reforma tributária")] == ["Reforma tributária avança no Senado"]
    assert hist.buscar("") == [] and hist.buscar('"; DROP TABLE artigos; --') == []  # consulta segura
    assert hist.titulos_recentes(14, AGORA) == ["Chuva forte atinge a capital"]
    assert hist.limpar(90, AGORA) == 1 and hist.buscar("reforma") == []


def test_sources_can_be_turned_off_without_losing_history(hist):
    hist.salvar_fonte(Fonte("G1", "https://g1.globo.com/rss", nota=8, medida=True))
    hist.salvar_fonte(Fonte("Blog", "https://blog.com/feed", "especialista", "pt", 6))
    hist.registrar([art("Algo do G1", "G1")], agora=AGORA)
    assert hist.ativar("g1", False) is True and hist.ativar("nao existe", False) is False
    assert [f.nome for f in hist.fontes(so_ativas=True)] == ["Blog"]
    assert [f.nome for f in hist.fontes()] == ["G1", "Blog"] and hist.buscar("algo")  # histórico fica


def test_execution_log(hist):
    assert hist.ultima_execucao() is None
    hist.registrar_execucao("2026-10-20", AGORA, 40, 12, 7, ["Blog: timeout"], "PASS")
    ultima = hist.ultima_execucao()
    assert ultima["escolhidos"] == 7 and "timeout" in ultima["falhas"]


# ── pontuação ────────────────────────────────────────────────────────────

def nota(artigo, **kw):
    args = dict(palavras_chave=["inteligência artificial", "ia"], entidades=[], janela_horas=24, titulos_recentes=[], agora=AGORA)
    args.update(kw)
    return pontuacao.pontuar(artigo, **args)


def test_each_component_adds_what_the_rules_say():
    base, _ = nota(art("Show da banda no sábado", nota=0.0, horas=24), palavras_chave=[])
    assert base == 15  # só "inédito": fonte 0, sem relevância, sem frescor
    relevante, motivos = nota(art("Inteligência artificial muda o jornalismo", nota=0.0, horas=24))
    assert relevante == base + 16 and "bate com: inteligência artificial" in motivos[0]
    assert nota(art("Show da banda", nota=10.0, horas=24), palavras_chave=[])[0] == base + 20
    assert nota(art("Show da banda", nota=0.0, horas=12), palavras_chave=[])[0] == base + 5  # frescor linear
    assert nota(art("Show da banda", nota=0.0, horas=24), palavras_chave=[], titulos_recentes=["Show da banda no sábado"])[0] == 0
    impacto, motivos = nota(art("Governo aprova lei de 2 bilhões", nota=0.0, horas=24), palavras_chave=[])
    assert impacto >= base + 10 and any("impacto" in m for m in motivos)
    seguida, _ = nota(art("Empresa Acme anuncia produto", nota=0.0, horas=24), palavras_chave=[], entidades=["Acme"])
    assert seguida > base


def test_clickbait_is_penalized_and_score_is_clamped():
    normal, _ = nota(art("Prefeitura divulga calendário de obras", nota=5.0))
    isca, motivos = nota(art("10 motivos para você não vai acreditar nesse calendário", nota=5.0))
    assert isca <= normal - 20 and any("clickbait" in m for m in motivos)
    assert 0 <= nota(art("Chocante: 7 dicas", nota=0.0, horas=500), palavras_chave=[], titulos_recentes=["Chocante: 7 dicas"])[0] <= 100
    maximo, _ = nota(art("IA: governo aprova lei de inteligência artificial com 2 bilhões", nota=10.0, horas=0.1))
    assert maximo <= 100


def test_sponsored_detection():
    assert pontuacao.eh_patrocinado(art("Publieditorial: conheça o novo carro"))
    assert pontuacao.eh_patrocinado(art("Notícia", resumo="Aproveite o cupom de desconto"))
    assert not pontuacao.eh_patrocinado(art("Banco Central mantém os juros"))


# ── curadoria ────────────────────────────────────────────────────────────

def test_filters_window_missing_date_sponsored_and_blocked():
    artigos = [art("Dentro da janela"), art("Muito antigo", horas=48), art("Sem data"), art("Publieditorial do banco"),
               art("Fofoca sobre celebridade famosa"), art("No futuro", horas=-5)]
    artigos[2].quando = 0
    aceitos, descartes = curadoria.filtrar(artigos, ["fofoca"], 24, AGORA)
    assert [a.titulo for a in aceitos] == ["Dentro da janela"]
    assert descartes == {"fora_da_janela": 2, "sem_data": 1, "patrocinado": 1, "bloqueado": 1}


def test_choose_5_plus_2_with_source_cap_minimum_and_tiebreak():
    itens = [Item(art(f"Notícia {i}", "A" if i < 5 else chr(66 + i % 6), horas=i), nota=90 - i) for i in range(12)]
    escolhidos = curadoria.escolher(itens, 5, 2, 2, 30)
    assert len(escolhidos) == 7
    assert [i.papel for i in escolhidos] == ["principal"] * 5 + ["radar"] * 2
    assert max(sum(1 for i in escolhidos if i.artigo.fonte == f) for f in {i.artigo.fonte for i in escolhidos}) <= 2
    assert all(i.nota >= 30 for i in escolhidos)
    fracos = [Item(art("Fraco 1", "X"), nota=10), Item(art("Fraco 2", "Y"), nota=29)]
    assert curadoria.escolher(fracos) == []
    empate = [Item(art("Velho", "P", horas=5), nota=50), Item(art("Novo", "Q", horas=1), nota=50)]
    assert [i.artigo.titulo for i in curadoria.escolher(empate)] == ["Novo", "Velho"]  # desempate: mais recente

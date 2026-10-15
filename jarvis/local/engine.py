"""Cérebro local: a Jarvis funcionando SEM IA generativa.

Entende comandos do dia a dia por regras (português) e executa direto: abrir programas,
sites, pastas e projetos; estado do PC; clima; notícias; vagas; hora e data; pesquisa na
internet com resumo extrativo. É sempre o último cérebro do roteador (a Jarvis nunca
fica sem resposta) e o primeiro para comandos diretos (rápido e sem gastar limite).
"""

from __future__ import annotations

import re
from datetime import datetime

from jarvis.brains.base import Answer, Message
from jarvis.local import websearch

WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
          "outubro", "novembro", "dezembro"]
NOTE = "\n\n_(modo independente: respondido sem IA)_"

HELP = (
    "Estou no **modo independente** (sem IA disponível agora). Ainda consigo:\n"
    "- **abrir** programas, sites, pastas e projetos (\"abre o WhatsApp\", \"abre github.com\")\n"
    "- **estado do PC** e programas pesados (\"como está o PC?\")\n"
    "- **clima**, **notícias** (gerais ou de tecnologia) e **vagas**\n"
    "- **hora e data**\n"
    "- **pesquisar na internet** e resumir com frases dos próprios sites (\"pesquise sobre ...\")"
)


# Palavras que disparam comandos: corrigidas por semelhança se vierem com erro de digitação.
VOCABULARY = """abre abra abrir inicia executa entra horas hora dia data hoje programas processos pesados
consumindo computador memoria disco clima previsao chover temperatura noticias tecnologia vagas pesquise
pesquisa procure busque ajuda comandos como esta status""".split()
_POLITE = re.compile(r"^((por favor|pfv|pf)[\s,]+|((voce|vc)\s+)?(pode|poderia|consegue|conseguiria)\s+(me\s+)?)+")


def _fix_typos(text: str) -> str:
    import difflib

    words = []
    for word in text.split():
        if len(word) >= 4 and word not in VOCABULARY:
            close = difflib.get_close_matches(word, VOCABULARY, n=1, cutoff=0.8)
            word = close[0] if close else word
        words.append(word)
    return " ".join(words)


def clean(text: str) -> str:
    text = websearch.fold(text).strip()
    text = re.sub(r"^(ei|ok|hey|oi|ola)?[\s,]*jarvis[\s,:!.]*", "", text)
    text = re.sub(r"[?!.]+$", "", text).strip()
    text = re.sub(r"[\s,]+(por favor|pfv)$", "", _POLITE.sub("", text))
    return _fix_typos(text)


class LocalEngine:
    name = "local"

    def __init__(self, load_config=None, brave_key=None) -> None:
        from jarvis import config, keys

        self._load_config = load_config or config.load
        self._brave_key = brave_key or (lambda: keys.get_key("brave"))

    # ── classificação ────────────────────────────────────────────────────
    PATTERNS = [
        ("abrir", r"^(abr[ae]|abrir|abre pra mim|inici[ae]|execut[ae]|entr[ae] n[oa])\s+(?P<alvo>.+)$"),
        ("hora", r"\b(que horas?|hora atual|horas sao)\b"),
        ("data", r"\b(que dia e hoje|data de hoje|qual (a|e a) data|que dia e)\b"),
        ("processos", r"\b(processos|programas)\b.*\b(pesad\w*|mais us\w*|consum\w*)\b"),
        ("pc", r"\b(como (esta|ta) (o\s+)?(meu\s+)?(pc|computador)|status do (pc|computador)|uso de (ram|cpu|memoria|disco)|"
               r"memoria ram|quanto de (ram|memoria|disco))\b"),
        ("clima", r"\b(clima|previsao do tempo|vai chover|temperatura)\b(\s+(em|de|no|na)\s+(?P<cidade>.+))?"),
        ("noticias", r"\bnoticias?\b"),
        # Só pedidos de vagas ("lembre que prefiro vagas remotas" não é um pedido).
        ("vagas", r"^((tem|ha|existe\w*|quero|ver|mostr\w*|me mostr\w*|procur\w*|busc\w*|busqu\w*|lista\w*|quais)\b.{0,25}\bvagas?\b|vagas?\b)"),
        ("ajuda", r"^(ajuda|o que voce (faz|sabe fazer)|comandos|me ajuda)$"),
        ("pesquisa", r"^(pesquis\w*|procur\w*|busc\w*|busqu\w*|me fale sobre|fale sobre)\s+"
                     r"(informac\w+\s+)?(sobre\s+|de\s+)?(?P<tema>.+)$"),
    ]
    DIRECT = {"abrir", "hora", "data", "processos", "pc", "clima", "noticias"}

    def classify(self, text: str) -> tuple[str, dict] | None:
        low = clean(text)
        for intent, pattern in self.PATTERNS:
            match = re.search(pattern, low)
            if match:
                return intent, {k: v for k, v in match.groupdict().items() if v}
        return None

    def is_direct_command(self, text: str) -> bool:
        """Comando curto que o motor local resolve sozinho (vai antes da IA, sem gastar limite)."""
        if len(text) > 80 or " e " in clean(text):  # "abre X e analisa Y" fica com a IA
            return False
        found = self.classify(text)
        return bool(found and found[0] in self.DIRECT)

    # ── execução ─────────────────────────────────────────────────────────
    def ask(self, messages: list[Message], system: str = "") -> Answer:
        text = messages[-1]["content"] if messages else ""
        return Answer(text=self.handle(text) + NOTE, brain="local")

    def handle(self, text: str) -> str:
        found = self.classify(text)
        intent, args = found if found else ("pergunta", {})
        handler = getattr(self, f"_{intent}")
        try:
            return handler(text, **args)
        except Exception as exc:  # nunca derruba a conversa
            return f"Tentei, mas não consegui: {exc}"

    def _abrir(self, text: str, alvo: str = "") -> str:
        from jarvis.dev import projects
        from jarvis.pc import launcher

        alvo = re.sub(r"^(o|a|os|as|meu|minha|programa|aplicativo|app)\s+", "", alvo).strip()
        cfg = self._load_config()
        target = re.sub(r"^projeto\s+", "", alvo)
        try:
            projects.resolve(cfg, target)
            return launcher.open_project(cfg, target)
        except ValueError:
            pass
        if alvo.startswith("pasta "):
            return launcher.open_folder(alvo[6:])
        if alvo in {f.replace("_", " ") for f in launcher.special_folders()}:
            return launcher.open_folder(alvo)
        if alvo.startswith(("site ", "http")) or re.search(r"\.[a-z]{2,}(/|$)", alvo):
            return launcher.open_site(alvo.removeprefix("site ").strip())
        return launcher.open_app(alvo)

    def _hora(self, text: str) -> str:
        return f"Agora são {datetime.now():%H:%M}."

    def _data(self, text: str) -> str:
        now = datetime.now()
        return f"Hoje é {WEEKDAYS[now.weekday()]}, {now.day} de {MONTHS[now.month - 1]} de {now.year}."

    def _pc(self, text: str) -> str:
        from jarvis.pc import system

        o = system.overview()
        lines = [f"**CPU:** {o['cpu_uso_percent']}% · **RAM:** {o['ram_em_uso_percent']}% em uso "
                 f"({o['ram_livre_gb']} GB livres de {o['ram_total_gb']} GB) · **Disco C:** {o['disco_c_livre_gb']} GB livres"]
        if o["ram_em_uso_percent"] >= 85:
            top = system.top_processes("memoria", 3)
            lines.append("A RAM está alta. Os que mais usam: " +
                         ", ".join(f"{p['nome']} ({p['memoria_mb']} MB)" for p in top) + ".")
        return "\n".join(lines)

    def _processos(self, text: str) -> str:
        from jarvis.pc import system

        top = system.top_processes("cpu" if "cpu" in clean(text) else "memoria", 5)
        return "Programas que mais consomem agora:\n" + "\n".join(
            f"- {p['nome']}: {p['memoria_mb']} MB, CPU {p['cpu_percent']}%" for p in top)

    def _clima(self, text: str, cidade: str = "") -> str:
        from jarvis.info import weather

        city = cidade or self._load_config().city
        if not city:
            return "Diga a cidade: \"clima em Fortaleza\"."
        return weather.sentence(weather.forecast(city))

    def _noticias(self, text: str) -> str:
        from jarvis.info import news

        kind = "tecnologia" if re.search(r"tecnolog|tech|ti\b", clean(text)) else "gerais"
        items = news.headlines(kind, 5)["manchetes"]
        return f"**Notícias {'de tecnologia' if kind == 'tecnologia' else 'de hoje'}:**\n" + "\n".join(
            f"- {h['titulo']} ({h['fonte']}) {h['link']}" for h in items)

    def _vagas(self, text: str) -> str:
        from jarvis import memory_db
        from jarvis.info import jobs

        profile, _ = jobs.load_profile(memory_db.open_memory(self._load_config()))
        if jobs.profile_is_empty(profile):
            return "Seu perfil profissional está vazio: me diga sua stack, nível e modalidade que eu anoto."
        found = jobs.find(profile, 5)["vagas"]
        if not found:
            return "Não achei vagas novas compatíveis agora."
        return "**Vagas para você:**\n" + "\n".join(
            f"- {j['titulo']} — {j['local']} (nota {j['nota']}, {j['fonte']}) {j['link']}" for j in found)

    def _ajuda(self, text: str) -> str:
        return HELP

    def _pesquisa(self, text: str, tema: str = "") -> str:
        return websearch.format_answer(tema, websearch.research(tema, 5, brave_key=self._brave_key()))

    def _pergunta(self, text: str) -> str:
        """Sem comando reconhecido: perguntas viram pesquisa na internet; o resto, ajuda."""
        low = clean(text)
        if len(low.split()) >= 2 and (text.strip().endswith("?") or re.match(
                r"^(o que|quem|qual|quais|como|quando|onde|por que|porque|quanto|explique|defina)\b", low)):
            return self._pesquisa(text, tema=low)
        return HELP

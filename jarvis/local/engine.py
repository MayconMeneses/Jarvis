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
from jarvis.local import agenda_skills, dev_skills, ensino, entendimento, evolucao, engenharia_skills, habilidades_skills, instagram_skills, llm_skills, mcp_skills, perfil_usuario_skills, radar_skills, skills, uso_skills, websearch
from jarvis.local.padroes import PATTERNS
from jarvis.local.ajuda import HELP  # noqa: F401 (o texto mora em ajuda.py; outros módulos importam daqui)

WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
          "outubro", "novembro", "dezembro"]
NOTE = "\n\n_(modo independente: respondido sem IA)_"


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
        self._generico = False  # a última resposta caiu no fallback genérico (ver ask)
        self._pendente = None  # opções de um "Você quis dizer" aguardando 1, 2 ou 3 (ver entendimento.py)

    # ── classificação ────────────────────────────────────────────────────
    PATTERNS = PATTERNS  # a lista mora em padroes.py (limite de 300 linhas por arquivo)
    MODULOS = {**agenda_skills.MODULOS, "padrao": lambda t, c: engenharia_skills.padrao(t), "ux_ferramenta": lambda t, c: engenharia_skills.ux_ferramenta(t),
               "gerar": lambda t, c: engenharia_skills.gerar_artefato(t), "criar_com_ia": llm_skills.criar,
               "llm_instalar": llm_skills.instalar, "llm_status": llm_skills.status, "avaliar_llm": llm_skills.avaliar,
               "aprender": llm_skills.aprender, "uso_ia": uso_skills.responder, "perfil_usuario": perfil_usuario_skills.responder, "revisar": lambda t, c: engenharia_skills.revisar(t), "radar": radar_skills.comando, **instagram_skills.MODULOS, **mcp_skills.MODULOS}
    DIRECT = {"uso_ia", "abrir", "hora", "data", "processos", "pc", "clima", "noticias", "sessoes", "dashboard", "ficha", "projetos", "perfil", "perfil_usuario", "radar", "vocabulario", "evolucao_relatorio", "ensinar", "esquecer_aprendizado"} | instagram_skills.INTENTS | agenda_skills.DIRETOS | mcp_skills.INTENTS

    def classify(self, text: str) -> tuple[str, dict] | None:
        low = clean(text)
        for intent, pattern in self.PATTERNS:
            match = re.search(pattern, low)
            if match:
                return intent, {k: v for k, v in match.groupdict().items() if v}
        return None

    def is_direct_command(self, text: str) -> bool:
        """Comando curto que o motor local resolve sozinho (vai antes da IA, sem gastar limite)."""
        found = self.classify(text)
        if not found or found[0] not in self.DIRECT or (len(text) > 80 and found[0] not in instagram_skills.INTENTS and found[0] not in ("radar", "perfil_usuario")):
            return False
        # "abre X e analisa Y" fica com a IA; em "meu nível é pleno" o "é" faz parte do comando.
        return found[0] in ("perfil", "perfil_usuario", "agenda_proximo", "radar") or found[0] in instagram_skills.INTENTS or " e " not in clean(text)

    # ── execução ─────────────────────────────────────────────────────────
    def ask(self, messages: list[Message], system: str = "") -> Answer:
        text = messages[-1]["content"] if messages else ""
        self._generico = False  # entendimento.fallback liga se só restou o bloco "não entendi"
        resposta = self.handle(text)
        if self._generico:  # conversa aberta e nenhum cérebro generativo: o caminho para ligar um, não o bloco genérico
            from jarvis.conversa import sem_cerebro

            self._pendente = None  # as opções do bloco trocado não aparecem mais: "1" não pode executar nada escondido
            resposta = sem_cerebro.texto(text, getattr(self._load_config(), "somente_independente", False))
        return Answer(text=resposta + NOTE, brain="local")

    # Pedidos genéricos (algoritmo, pesquisa...) que podem, na verdade, ser uma pergunta sobre a própria Jarvis.
    GENERICOS = {"algoritmo", "tecnologia", "pesquisa"}

    def handle(self, text: str) -> str:
        escolha = entendimento.escolher_pendente(self, text)
        if escolha is not None:
            return escolha
        found = self.classify(text)
        intent, args = found if found else ("pergunta", {})
        try:
            if intent == "pergunta" or intent in self.GENERICOS:
                sobre_mim = entendimento.apelido(self, text) if intent == "pergunta" else None
                if sobre_mim is not None:
                    return sobre_mim
                c = entendimento.conhecimento_alto(text)
                if c is not None:
                    return entendimento.executar(self, c, text)
                duvida = entendimento.duvida_sobre_mim(self, text)
                if duvida is not None:
                    return duvida
            return self.executar(intent, text, args)
        except Exception as exc:  # nunca derruba a conversa
            return f"Tentei, mas não consegui: {exc}"

    def executar(self, intent: str, text: str, args: dict) -> str:
        if intent in self.MODULOS:
            return self.MODULOS[intent](text, self._load_config())
        return getattr(self, f"_{intent}")(text, **args)

    def _ensinar(self, text: str) -> str:
        return ensino.propor(self, text)

    def _vocabulario(self, text: str) -> str:
        return evolucao.vocabulario()

    def _evolucao_relatorio(self, text: str) -> str:
        return evolucao.relatorio()[0]

    def _esquecer_aprendizado(self, text: str) -> str:
        return evolucao.esquecer()

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

    def _sessoes(self, text: str) -> str:
        return skills.sessions_waiting()

    def _dashboard(self, text: str) -> str:
        return skills.dashboard(text)

    def _anotar_projeto(self, text: str) -> str:
        return skills.project_note(text, self._load_config())

    def _ficha(self, text: str) -> str:
        return skills.project_card(text, self._load_config())

    def _projetos(self, text: str) -> str:
        return skills.projects_list(self._load_config())

    def _perfil(self, text: str) -> str:
        return skills.profile(text, self._load_config())

    def _memoria(self, text: str) -> str:
        return skills.recall(text, self._load_config())

    def _lembrar(self, text: str) -> str:
        return skills.remember(text, self._load_config()) + "\n\n" + skills.forget_hint()

    def _avaliar_projeto(self, text: str) -> str:
        return habilidades_skills.evaluate(text, self._load_config())

    def _habilidades(self, text: str) -> str:
        return habilidades_skills.overview()

    def _evoluir(self, text: str) -> str:
        if "plano" in clean(text):
            return habilidades_skills.plan(text)
        return habilidades_skills.evolve(text, self._load_config())

    def _checklist(self, text: str) -> str:
        return habilidades_skills.checklist(text)

    def _criar_sistema(self, text: str) -> str:
        return dev_skills.create_system(text, self._load_config())

    def _comparar(self, text: str) -> str:
        return dev_skills.compare(text)

    def _recomendar(self, text: str) -> str:
        return dev_skills.recommend(text)

    def _algoritmo(self, text: str) -> str:
        """Algoritmo pronto, se for um clássico; senão, é uma pergunta comum e vai para a pesquisa."""
        return dev_skills.algorithm(text) or self._pesquisa(text, tema=clean(text))

    def _logica(self, text: str) -> str:
        return dev_skills.logic(text)

    def _tecnologia(self, text: str, tema: str = "") -> str:
        """Explica a tecnologia se ela estiver na base; senão, pesquisa na internet como antes."""
        return dev_skills.info(tema) or self._pesquisa(text, tema=clean(text))  # a pergunta inteira vai para a busca

    def _ajuda(self, text: str) -> str:
        return HELP

    def _pesquisa(self, text: str, tema: str = "") -> str:
        if re.match(r"^busc", clean(text)) and dev_skills.algorithm(text):
            return dev_skills.algorithm(text)  # "busca binária em Java" é um algoritmo, não uma pesquisa na web
        return websearch.format_answer(tema, websearch.research(tema, 5, brave_key=self._brave_key()))

    def _pergunta(self, text: str) -> str:
        """Sem comando reconhecido: algoritmo/comparação conhecidos; o resto vai para o entendimento (casador, "você quis dizer")."""
        low = clean(text)
        if dev_skills.algorithm(text):
            return dev_skills.algorithm(text)  # "quicksort em C#": só o nome do algoritmo e a linguagem
        if re.search(r"\bou\b", low) and (len(dev_skills.conhecimento.mentioned(text)) >= 2 or len(dev_skills.logica.mentioned_concepts(text)) >= 2):
            return dev_skills.compare(text)  # "Python ou Node?", "pilha ou fila?"
        return entendimento.fallback(self, text, self._load_config())

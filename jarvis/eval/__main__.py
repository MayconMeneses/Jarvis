"""Roda os benchmarks e salva o relatório.

    python -m jarvis.eval                       comandos, robustez e resumos (sem gastar IA)
    python -m jarvis.eval --ias claude,gemini   + respostas dos cérebros (gasta limite)
    python -m jarvis.eval --juiz claude         + juiz por rubrica (substituto do BLEURT)
    python -m jarvis.eval --sem-semantica       pula o BERTScore (não baixa o MiniLM)
"""

from __future__ import annotations

import argparse
import sys
import time

from jarvis import config, memory_db
from jarvis.eval import bench


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="jarvis.eval")
    parser.add_argument("--ias", default="", help="cérebros a avaliar: claude,gemini,nvidia,local")
    parser.add_argument("--juiz", default="", help="cérebro que faz a avaliação por rubrica")
    parser.add_argument("--sem-semantica", action="store_true")
    parser.add_argument("--json", default="", help="grava um resumo numérico (para a verificação automática)")
    args = parser.parse_args(argv)

    encoder = None
    if not args.sem_semantica:
        from jarvis.eval import semantic

        print("Carregando o modelo semântico (MiniLM multilíngue)…")
        encoder = semantic.default_encoder()

    from jarvis.local.engine import LocalEngine

    cfg = config.load()
    print("1-2/ Comandos e robustez…")
    commands = bench.bench_commands(LocalEngine())
    print("3/ Resumos…")
    summaries = bench.bench_summaries(encoder)

    answers = None
    if args.ias or args.juiz:
        from jarvis.brains import build_router

        by_name = {b.name: b for b in build_router(cfg).brains}
        chosen = [by_name[n] for n in args.ias.split(",") if n in by_name]
        judge = by_name.get(args.juiz)
        print(f"4/ Respostas de: {', '.join(b.name for b in chosen) or '—'}…")
        answers = bench.bench_answers(chosen, encoder, judge)
        for brain in by_name.values():
            if hasattr(brain, "stop"):
                brain.stop()

    if args.json:
        import json
        from pathlib import Path

        Path(args.json).write_text(json.dumps(bench.numeric_summary(commands, summaries)), encoding="utf-8")
        print(f"Resumo numérico em {args.json}")
        return 0

    report = bench.report_markdown(commands, summaries, answers, encoder is not None)
    print("\n" + report)
    ref = memory_db.open_memory(cfg).put(f"Avaliações/{time.strftime('%Y-%m-%d %H%M')} Avaliação", report, "relatorio")
    print(f"\nRelatório salvo na memória da Jarvis: {ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

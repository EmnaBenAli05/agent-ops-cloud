"""Ligne de commande.

    python -m agent_ops ALT-001 --offline     # démo sans clé d'API (faux LLM)
    python -m agent_ops ALT-001               # appel réel à Claude (ANTHROPIC_API_KEY)
    python -m agent_ops ALT-001 --auto-deny   # refuse toute action sensible sans demander
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import deny_all, run_agent
from .audit import AuditLog
from .llm import dump


def ask_operator(tool_name: str, tool_input: dict) -> bool:
    print("\n" + "=" * 60)
    print("VALIDATION HUMAINE REQUISE")
    print(f"Action proposée : {tool_name} {dump(tool_input)}")
    try:
        answer = input("Approuver ? [o/N] ").strip().lower()
    except EOFError:  # pas de clavier (script, CI) : refus par défaut
        answer = ""
        print("(aucune réponse : refus)")
    print("=" * 60)
    return answer in ("o", "oui", "y", "yes")


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent_ops", description=__doc__.splitlines()[0])
    parser.add_argument("alert_id", help="ex. ALT-001, ALT-002, ALT-003")
    parser.add_argument("--offline", action="store_true", help="faux LLM déterministe, sans réseau")
    parser.add_argument("--auto-deny", action="store_true", help="refuse toute action sensible")
    parser.add_argument("--audit", default="logs/audit.jsonl", help="fichier du journal d'audit")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.offline:
        from .llm import ScriptedBackend
        backend = ScriptedBackend()
    else:
        from .llm import ClaudeBackend
        backend = ClaudeBackend()

    approver = deny_all if args.auto_deny or not sys.stdin.isatty() else ask_operator
    audit = AuditLog(Path(args.audit))
    result = run_agent(args.alert_id, backend, approver=approver, audit=audit, on_step=print)

    print("\n" + result.report)
    print(f"\n[{result.stop} en {result.rounds} tours ; audit : {args.audit}]")
    return 0 if result.stop == "end_turn" else 1


if __name__ == "__main__":
    raise SystemExit(main())

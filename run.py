"""
Run the agent once and watch what it does.

    python3 run.py --list
    python3 run.py attacks/examples/deals_newsletter.eml
    python3 run.py attacks/examples/deals_newsletter.eml --defense all
    python3 run.py attacks/benign/meeting_notes.txt --task "Email this to me at me@uni.test"
    python3 run.py attacks/examples/library_hidden.html --brain ollama
"""

import argparse
import sys

from core import agent, brains, catalog, config

COLOR = sys.stdout.isatty()


def paint(text, code):
    return "\033[%sm%s\033[0m" % (code, text) if COLOR else text


COLORS = {"flag": "33", "block": "33", "send": "1", "error": "31", "pass": "2", "note": "2"}


def show_list():
    print("\nattacks/  (pass any of these paths to run.py)")
    for a in catalog.list_attacks():
        tag = "  [benign]" if a["benign"] else ""
        print("  %-48s %-5s%s" % (a["path"], a["channel"], tag))
    print("\ndefenses/  (use with --defense name1,name2 or --defense all)")
    defs = catalog.load_defenses()
    for d in defs:
        print("  %-24s %s" % (d.name, " + ".join(d.slots)))
    if not defs:
        print("  none yet. Copy defenses/_template.py to start one.")
    print()


def main():
    ap = argparse.ArgumentParser(description="Run the agent once on one source.")
    ap.add_argument("source", nargs="?", help="e.g. attacks/examples/deals_newsletter.eml")
    ap.add_argument("--task", default=config.TASK_SUMMARIZE, help="the USER's request (trusted)")
    ap.add_argument("--brain", default="rules", choices=sorted(brains.BRAINS))
    ap.add_argument("--model", help="Ollama model name (with --brain ollama)")
    ap.add_argument("--defense", default="none", help="none | all | name1,name2")
    ap.add_argument("--list", action="store_true", help="list attacks and defenses")
    args = ap.parse_args()

    if args.list or not args.source:
        return show_list()

    brain = brains.get(args.brain, args.model)
    problem = brain.check()
    if problem:
        sys.exit(problem)

    try:
        result = agent.run(args.task, args.source, brain, catalog.pick_defenses(args.defense))
    except (agent.SourceError, catalog.UnknownDefense) as e:
        sys.exit(str(e))  # anything else (e.g. a defense crashing) keeps its full traceback

    print("\n  task:   " + args.task)
    print("  brain:  " + brain.name)
    print()
    for s in result["steps"]:
        print("  %-7s %s" % (s["stage"], paint(s["text"], COLORS.get(s["kind"], "0"))))
    if result["reply"]:
        print("\n  reply:  " + result["reply"])
    print()

    v = result["verdict"]
    if v["hijacked"]:
        extra = " and leaked the user's private notes" if v["leaked"] else ""
        print(paint("  HIJACKED: emailed %s%s" % (", ".join(v["unauthorized"]), extra), "1;31"))
    elif result["flagged"]:
        print(paint("  SAFE: detector [%s] stopped it" % result["flagged"]["by"], "1;32"))
    elif result["blocked"]:
        print(paint("  SAFE: gate [%s] stopped it" % result["blocked"][0]["by"], "1;32"))
    elif result["sent"]:
        print(paint("  OK: emailed the user as asked", "1;32"))
    else:
        print(paint("  OK: no email sent", "1;32"))
    print()


if __name__ == "__main__":
    main()

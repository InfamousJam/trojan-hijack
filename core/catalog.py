"""
Finds attacks and defenses on disk, so partners only ever add files.

  attacks/<category>/<name>.eml|.html|.txt   found by list_attacks()
  defenses/<name>.py                         found by load_defenses()

Anything whose name starts with "_" or "." is skipped, and so are README files.
"""

import importlib.util
import sys
from pathlib import Path

from core import config, tools

BENIGN = "benign"  # the attacks/ folder that holds the clean control inputs


class UnknownDefense(ValueError):
    """--defense named a file that isn't in defenses/."""


def _hidden(name):
    return name.startswith(("_", "."))


def list_attacks():
    """Every input the agent can be tested on, sorted by category then name."""
    out = []
    for p in sorted(config.ATTACKS.rglob("*")):
        rel = p.relative_to(config.ATTACKS)
        if not p.is_file() or any(_hidden(part) for part in rel.parts) or p.stem.upper() == "README":
            continue
        channel = tools.channel_of(p)
        if channel is None:
            continue
        category = rel.parts[0] if len(rel.parts) > 1 else "misc"
        out.append({
            "path": (Path("attacks") / rel).as_posix(),
            "name": rel.as_posix(),
            "category": category,
            "channel": channel,
            "benign": category == BENIGN,
        })
    return out


class Defense:
    """One file in defenses/. It can define detect(), gate(), or both."""

    def __init__(self, name, module):
        self.name = name
        self.label = getattr(module, "NAME", name)
        self.detect = getattr(module, "detect", None)
        self.gate = getattr(module, "gate", None)
        self.slots = [s for s in ("detect", "gate") if getattr(self, s)]

    def info(self):
        return {"name": self.name, "label": self.label, "slots": self.slots}


def load_defenses():
    """Import every defenses/*.py fresh (so edits show up without restarting)."""
    if str(config.DEFENSES) not in sys.path:
        sys.path.insert(0, str(config.DEFENSES))  # lets defenses import their own _helpers.py
    found = []
    for p in sorted(config.DEFENSES.glob("*.py")):
        if _hidden(p.name):
            continue
        spec = importlib.util.spec_from_file_location("defense_" + p.stem, p)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        d = Defense(p.stem, module)
        if d.slots:
            found.append(d)
        else:
            print("note: defenses/%s has no detect() or gate(), skipping it" % p.name, file=sys.stderr)
    return found


def pick_defenses(spec, available=None):
    """'none' | 'all' | 'name1,name2'  ->  list of Defense"""
    available = load_defenses() if available is None else available
    spec = (spec or "none").strip()
    if spec == "none":
        return []
    if spec == "all":
        return available
    by_name = {d.name: d for d in available}
    picked = []
    for name in (n.strip() for n in spec.split(",") if n.strip()):
        if name not in by_name:
            raise UnknownDefense("no defense named %r in defenses/ (have: %s)" % (name, ", ".join(by_name) or "none yet"))
        picked.append(by_name[name])
    return picked


def verdict(value):
    """Accept (bool, reason) or a bare bool from a defense."""
    if isinstance(value, (tuple, list)):
        reason = str(value[1]) if len(value) > 1 and value[1] else ""
        return bool(value[0]), reason or "no reason given"
    return bool(value), "no reason given"

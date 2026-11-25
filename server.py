"""
The web demo. Run:  python3 server.py   then open http://localhost:8000

It only listens on 127.0.0.1, so nothing outside this machine can reach it.
Attacks and defenses are re-read on every request: add a file, refresh the page.

Routes:
  GET  /                    the demo page (web/index.html)
  GET  /api/catalog         attacks (with sender/subject/title), defenses, brains, preset tasks
  GET  /api/source?path=..  one attack file: raw text, plus the parsed email for .eml
  POST /api/run             {"task", "source", "brain", "defenses": [names]} -> result
  POST /api/evaluate        {"brain"} -> every attack x every defense setup (like evaluate.py)
  GET  /api/outbox          emails the stub has "sent"
  POST /api/outbox/clear    empty the outbox
"""

import email
import html
import json
import re
import sys
import traceback
from email import policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import evaluate
from core import agent, brains, catalog, config, tools

INDEX = config.ROOT / "web" / "index.html"


def read_outbox():
    if not config.OUTBOX.exists():
        return []
    return [json.loads(line) for line in config.OUTBOX.read_text(encoding="utf-8").splitlines() if line]


# ------------------------------------------------------------ for the mailbox view (display only)

def parse_email(text):
    """Headers and a readable body. The agent itself always gets the raw file."""
    msg = email.message_from_string(text, policy=policy.default)
    part = msg.get_body(preferencelist=("plain", "html")) or msg
    try:
        body = part.get_content()
    except Exception:
        body = part.get_payload()
    return {
        "from": str(msg["from"] or ""), "to": str(msg["to"] or ""),
        "subject": str(msg["subject"] or ""), "date": str(msg["date"] or ""),
        "body": body if isinstance(body, str) else "",
        "html": part.get_content_type() == "text/html",
    }


def first_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:140]
    return ""


def describe(attack):
    """What the mailbox list shows: sender and subject, page title, or first line."""
    try:
        text = tools.read_local(attack["path"])
        if attack["channel"] == "email":
            e = parse_email(text)
            body = re.sub(r"<[^>]+>", " ", e["body"]) if e["html"] else e["body"]
            return {"from": e["from"], "subject": e["subject"], "preview": first_line(body)}
        if attack["channel"] == "web":
            m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            return {"title": html.unescape(m.group(1)).strip() if m else ""}
        return {"preview": first_line(text)}
    except Exception:
        return {}


def get_source(path):
    text = tools.read_local(path)
    out = {"path": path, "text": text, "channel": tools.channel_of(path)}
    if out["channel"] == "email":
        out["email"] = parse_email(text)
    return out


# ------------------------------------------------------------ API

def get_catalog():
    defs = catalog.load_defenses()
    return {
        "attacks": [dict(a, meta=describe(a)) for a in catalog.list_attacks()],
        "defenses": [d.info() for d in defs],
        "brains": [{"name": n, "problem": brains.get(n).check()} for n in brains.BRAINS],
        "tasks": {"summarize": config.TASK_SUMMARIZE, "send": config.TASK_SEND},
        "user_name": config.USER_NAME,
        "user_email": config.USER_EMAIL,
        "canary": config.CANARY,
    }


def run_agent(data):
    available = catalog.load_defenses()
    wanted = set(data.get("defenses") or [])
    picked = [d for d in available if d.name in wanted]
    return agent.run(data.get("task", ""), data.get("source", ""), data.get("brain", "rules"), picked)


def run_evaluate(data):
    brain = brains.get(data.get("brain", "rules"))
    problem = brain.check()
    if problem:
        raise ValueError(problem)
    result = evaluate.run_all(brain, data.get("only") or None)
    result["saved"] = evaluate.save(result)
    return result


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, ctype="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def safely(self, fn):
        try:
            self.reply(200, fn())
        except (ValueError, agent.SourceError) as e:  # bad input: the message says it all
            self.reply(400, {"error": str(e)})
        except Exception as e:  # e.g. a defense crashed: keep the traceback in the terminal
            traceback.print_exc()
            self.reply(400, {"error": "%s: %s" % (type(e).__name__, e)})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            return self.reply(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/catalog":
            return self.safely(get_catalog)
        if url.path == "/api/source":
            path = parse_qs(url.query).get("path", [""])[0]
            return self.safely(lambda: get_source(path))
        if url.path == "/api/outbox":
            return self.safely(read_outbox)
        self.reply(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/run":
            return self.safely(lambda: run_agent(data))
        if self.path == "/api/evaluate":
            return self.safely(lambda: run_evaluate(data))
        if self.path == "/api/outbox/clear":
            config.OUTBOX.write_text("", encoding="utf-8")
            return self.reply(200, {"cleared": True})
        self.reply(404, {"error": "not found"})

    def log_message(self, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    try:
        server = ThreadingHTTPServer(("127.0.0.1", config.PORT), Handler)
    except OSError:
        sys.exit("port %d is busy (an old server still running?). Stop it, or run:  PORT=8001 python3 server.py"
                 % config.PORT)
    print("Trojan Hijack running at http://localhost:%d  (Ctrl+C to stop)" % config.PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

"""
The agent's tools. Readers return untrusted CONTENT. send_email is the one
sensitive action, and it is a stub that only appends to a local log.

The sandbox rules are enforced here, so nothing else has to think about them:
  - emails and files can only be read from inside attacks/
  - web pages can only be fetched from this machine (localhost / 127.0.0.1)
  - send_email never sends anything
"""

import json
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from core import config, webhost

# What an email address looks like. Shared by the brains and the judge.
ADDRESS = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"

CHANNELS = {
    ".eml": "email",
    ".html": "web", ".htm": "web",
    ".txt": "file", ".md": "file", ".csv": "file", ".json": "file",
}


def channel_of(path):
    """'email', 'web' or 'file', picked from the file extension. None if unknown."""
    return CHANNELS.get(Path(path).suffix.lower())


def _inside_attacks(path):
    p = (config.ROOT / path).resolve()
    if config.ATTACKS.resolve() not in p.parents:
        raise ValueError("only files inside attacks/ can be read: " + str(path))
    return p


def read_local(path):
    """Read an email or file from attacks/."""
    return _inside_attacks(path).read_text(encoding="utf-8")


def read_webpage(url):
    """Fetch a page. Only pages on this machine are allowed."""
    if urlparse(url).hostname not in ("localhost", "127.0.0.1"):
        raise ValueError("only pages on this machine can be fetched: " + url)
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.read().decode("utf-8", errors="replace")


def read_source(source):
    """
    One entry point for every reader. Returns (content, channel, location).
      'attacks/benign/prof_checkin.eml'      -> email
      'attacks/benign/meeting_notes.txt'     -> file
      'attacks/examples/library_hidden.html' -> web page, fetched over HTTP
      'http://127.0.0.1:8000/some/page'      -> web page at that local URL
    """
    if source.startswith(("http://", "https://")):
        return read_webpage(source), "web", source
    channel = channel_of(source)
    if channel in ("email", "file"):
        return read_local(source), channel, source
    if channel == "web":
        _inside_attacks(source)
        url = webhost.url_for(source)
        return read_webpage(url), "web", url
    raise ValueError("unknown file type (use .eml, .html, .txt, or a localhost URL)")


def read_private_notes():
    """The user's own private notes. The agent keeps them in context; attackers want them."""
    return (config.PRIVATE / "notes.txt").read_text(encoding="utf-8")


def addresses_in(text):
    return {a.lower() for a in re.findall(ADDRESS, text)}


def send_email(to, subject, body, outbox=None):
    """STUB. Appends the email to a local .jsonl log instead of sending it."""
    record = {"time": time.strftime("%H:%M:%S"), "to": to, "subject": subject, "body": body}
    with open(outbox or config.OUTBOX, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record

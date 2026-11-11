"""
A tiny web server that hosts the .html files in attacks/, so the agent reads
web pages over real HTTP the way a browsing agent would.

It starts by itself the first time a page is needed, on a free port, and only
listens on 127.0.0.1, so nothing outside this machine can reach it.
"""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

from core import config

_base = None
_lock = threading.Lock()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def base_url():
    global _base
    with _lock:
        if _base is None:
            handler = partial(_QuietHandler, directory=str(config.ATTACKS))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            _base = "http://127.0.0.1:%d/" % server.server_address[1]
    return _base


def url_for(path):
    """'attacks/examples/page.html' -> 'http://127.0.0.1:<port>/examples/page.html'"""
    rel = (config.ROOT / path).resolve().relative_to(config.ATTACKS.resolve())
    return base_url() + quote(rel.as_posix())

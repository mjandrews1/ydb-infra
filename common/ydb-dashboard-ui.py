#!/usr/bin/env python3
"""YottaDB Dashboard UI + metrics fan-in (U01/U02).

GET /         HTML dashboard
GET /metrics  Prometheus text (from ydbdash :9187 if up, else local gvstat)

No auth — bind via Caddy (portal / basicauth) only.
"""
from __future__ import annotations

import http.client
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.environ.get("YDB_DASH_HTML", os.path.join(HERE, "ydb-dashboard.html"))
YDB_DASH_PORT = int(os.environ.get("YOTTA_PROM_PORT", "9187"))
LISTEN_PORT = int(os.environ.get("YDB_DASH_UI_PORT", "9188"))


def fetch_upstream_metrics() -> str:
    try:
        c = http.client.HTTPConnection("127.0.0.1", YDB_DASH_PORT, timeout=3)
        c.request("GET", "/metrics")
        r = c.getresponse()
        data = r.read().decode("utf-8", "replace")
        c.close()
        if data.strip():
            return data
    except OSError:
        pass
    # fallback: one gvstatprom sample
    try:
        cmd = (
            "source /usr/local/etc/ydb_env_set >/dev/null 2>&1; "
            "ydb <<< 'D proc^gvstatprom(\"DEFAULT\")' 2>/dev/null | "
            "grep -Ev '(^YDB>)|(^$)'"
        )
        out = subprocess.check_output(["bash", "-lc", cmd], timeout=8).decode("utf-8", "replace")
        lines = []
        for part in out.replace("\n", ",").split(","):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            k, v = k.strip(), v.strip()
            if k and v.replace(".", "").isdigit():
                lines.append(f"{k}_pit {v}")
        return "# ydb-dashboard fallback gvstat\n" + "\n".join(lines) + "\n"
    except Exception as e:
        return f"# metrics unavailable: {e}\n"


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/metrics", "/dashboard/metrics"):
            body = fetch_upstream_metrics().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/", "/dashboard", "/dashboard/"):
            try:
                body = open(HTML_PATH, "rb").read()
            except OSError:
                body = b"<h1>dashboard html missing</h1>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def main() -> None:
    ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), H).serve_forever()


if __name__ == "__main__":
    main()

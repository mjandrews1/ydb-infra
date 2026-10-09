#!/usr/bin/env python3
"""Safe YottaDB dashboard metrics (Prometheus text).

Wraps gvstatprom without the upstream int('') crash. Serves /metrics.
"""
from __future__ import annotations

import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("YOTTA_PROM_PORT", "9187"))


def sample() -> str:
    env = os.environ.copy()
    # ydb_env_set
    script = (
        'source /usr/local/etc/ydb_env_set >/dev/null 2>&1; '
        'ydb <<< \'ZL "gvstatprom.m" D proc^gvstatprom("DEFAULT") H\' 2>/dev/null | '
        "grep -Ev '(^YDB>)|(^$)'"
    )
    try:
        out = subprocess.check_output(["bash", "-lc", script], timeout=10, env=env)
    except Exception as e:
        return f"# gvstat error: {e}\n"
    text = out.decode("utf-8", "replace")
    lines = ["# TYPE ydb_gvstat gauge"]
    for part in re.split(r"[,\s]+", text):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = re.sub(r"[^A-Za-z0-9_]", "_", k.strip())
        v = v.strip()
        if not k:
            continue
        try:
            fv = float(v)
        except ValueError:
            continue
        lines.append(f"ydb_{k} {fv}")
    # process/file counts via shell (cheap)
    for name, cmd in [
        ("ydb_procs", "pgrep -c yottadb || true"),
        ("ydb_loadavg1", "cut -d' ' -f1 /proc/loadavg"),
    ]:
        try:
            val = subprocess.check_output(["bash", "-lc", cmd], timeout=5).decode().strip()
            lines.append(f"{name} {float(val)}")
        except Exception:
            pass
    return "\n".join(lines) + "\n"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        return

    def do_GET(self):
        body = sample().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()

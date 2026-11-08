#!/usr/bin/env python3
"""Deterministic HTTP workload endpoint for the RAMP Docker laboratory."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CHUNK = b"RAMP-LAB-PAYLOAD-0123456789abcdef" * 2048
MAX_BYTES = 100 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = b"ramp-lab-destination-ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path != "/payload":
            self.send_error(404, "use /health or /payload?bytes=N")
            return

        try:
            requested = int(parse_qs(parsed.query).get("bytes", ["10485760"])[0])
        except (TypeError, ValueError):
            self.send_error(400, "bytes must be an integer")
            return
        if requested < 1 or requested > MAX_BYTES:
            self.send_error(400, "bytes must be between 1 and 104857600")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(requested))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        remaining = requested
        while remaining:
            block = CHUNK[: min(remaining, len(CHUNK))]
            self.wfile.write(block)
            remaining -= len(block)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()

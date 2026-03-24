#!/usr/bin/env python3
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

port = int(os.getenv("PORT", 8855))

STATUS_FILE = Path("/data/status.json")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.respond_json({"status": "ok"})
            return

        if self.path == "/status":
            if STATUS_FILE.exists():
                try:
                    data = json.loads(STATUS_FILE.read_text())
                except Exception:
                    data = {"error": "invalid_json"}
            else:
                data = {"error": "status_file_missing"}

            self.respond_json(data)
            return

        self.send_error(404, "Not Found")

    def respond_json(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

if __name__ == "__main__":
    main()
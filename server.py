#!/usr/bin/env python3
import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CleanURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def translate_path(self, path):
        translated = super().translate_path(path)
        if os.path.exists(translated):
            return translated
        # Check if adding .html resolves to a file (support clean URLs like /guide or /firmware)
        clean_html = translated + ".html"
        if os.path.isfile(clean_html):
            return clean_html
        return translated

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/local-portable-assets"):
            import json
            candidates = [
                ("/home/deck/Documents/Workspaces/UpdaterNeo/updater-ce-neo/dist/windows/InnioasisUpdater/Updater-CE-Windows-Portable.zip", "Updater-CE-Windows-Portable.zip"),
                ("/home/deck/Documents/Workspaces/UpdaterNeo/updater-ce-neo/dist/windows/InnioasisUpdater/Updater-CE-Windows-Portable.zip", "UpdaterCE-Windows-Portable.zip"),
                ("/home/deck/Documents/Workspaces/UpdaterNeo/updater-ce-neo/dist/linux/InnioasisUpdater/Updater-CE-Linux-Portable.zip", "Updater-CE-Linux-Portable.zip"),
                ("/tmp/linux_portable.zip", "Updater-CE-Linux-Portable.zip"),
                ("/tmp/linux_portable.zip", "UpdaterCE-Linux-Portable.zip"),
            ]
            found = []
            seen = set()
            for path, name in candidates:
                if os.path.isfile(path) and name not in seen:
                    seen.add(name)
                    found.append({
                        "name": name,
                        "browser_download_url": f"/local-portable/{name}",
                        "size": os.path.getsize(path)
                    })
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(found).encode("utf-8"))
            return

        if self.path.startswith("/local-portable/"):
            fname = self.path.split("/")[-1].split("?")[0]
            candidates = {
                "Updater-CE-Windows-Portable.zip": "/home/deck/Documents/Workspaces/UpdaterNeo/updater-ce-neo/dist/windows/InnioasisUpdater/Updater-CE-Windows-Portable.zip",
                "UpdaterCE-Windows-Portable.zip": "/home/deck/Documents/Workspaces/UpdaterNeo/updater-ce-neo/dist/windows/InnioasisUpdater/Updater-CE-Windows-Portable.zip",
                "Updater-CE-Linux-Portable.zip": "/tmp/linux_portable.zip",
                "UpdaterCE-Linux-Portable.zip": "/tmp/linux_portable.zip",
            }
            target_path = candidates.get(fname)
            if target_path and os.path.isfile(target_path):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(os.path.getsize(target_path)))
                self.end_headers()
                with open(target_path, "rb") as f:
                    while True:
                        buf = f.read(65536)
                        if not buf:
                            break
                        self.wfile.write(buf)
                return
            self.send_error(404, "Local portable package not found")
            return

        if self.path.startswith("/download-proxy?"):
            from urllib.parse import urlparse, parse_qs
            import urllib.request
            qs = parse_qs(urlparse(self.path).query)
            target = qs.get("url", [None])[0]
            if target and (target.startswith("https://github.com/") or target.startswith("https://objects.githubusercontent.com/") or target.startswith("https://release-assets.githubusercontent.com/") or target.startswith("https://raw.githubusercontent.com/")):
                try:
                    req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0 (Innioasis-Updater-Local)"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        self.send_response(200)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                        self.send_header("Access-Control-Allow-Headers", "*")
                        self.send_header("Content-Type", resp.headers.get("Content-Type", "application/octet-stream"))
                        cl = resp.headers.get("Content-Length")
                        if cl:
                            self.send_header("Content-Length", cl)
                        self.end_headers()
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                        return
                except Exception as e:
                    self.send_error(502, f"Proxy error: {e}")
                    return
            self.send_error(400, "Invalid target URL")
            return
        super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/download-proxy?"):
            from urllib.parse import urlparse, parse_qs
            import urllib.request
            qs = parse_qs(urlparse(self.path).query)
            target = qs.get("url", [None])[0]
            if target and (target.startswith("https://github.com/") or target.startswith("https://objects.githubusercontent.com/") or target.startswith("https://release-assets.githubusercontent.com/") or target.startswith("https://raw.githubusercontent.com/")):
                try:
                    req = urllib.request.Request(target, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (Innioasis-Updater-Local)"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        self.send_response(200)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
                        self.send_header("Access-Control-Allow-Headers", "*")
                        self.send_header("Content-Type", resp.headers.get("Content-Type", "application/octet-stream"))
                        cl = resp.headers.get("Content-Length")
                        if cl:
                            self.send_header("Content-Length", cl)
                        self.end_headers()
                        return
                except Exception as e:
                    self.send_error(502, f"Proxy error: {e}")
                    return
            self.send_error(400, "Invalid target URL")
            return
        super().do_HEAD()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            custom_404 = os.path.join(DIRECTORY, "404.html")
            if os.path.isfile(custom_404):
                try:
                    with open(custom_404, "rb") as f:
                        content = f.read()
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception:
                    pass
        super().send_error(code, message, explain)

def run():
    server_address = ("", PORT)
    with http.server.ThreadingHTTPServer(server_address, CleanURLHandler) as httpd:
        print(f"==================================================")
        print(f" Innioasis Updater website running locally!")
        print(f" URL: http://localhost:{PORT}")
        print(f" Root: {DIRECTORY}")
        print(f" Press Ctrl+C to stop the server.")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run()

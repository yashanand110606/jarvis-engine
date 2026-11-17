# jarvis_hud_server.py
import os, json, threading, time
from http.server import HTTPServer, BaseHTTPRequestHandler

HUD_HTML_PATH = os.path.join(os.getcwd(), "jarvis_hud.html")
PORT = 8001

state = {
    "cpu": 0, "mem": 0, "disk": 0, "uptime": "0h 0m",
    "message": ""
}

def update_system():
    try:
        import psutil
        state["cpu"] = int(psutil.cpu_percent(interval=1))
        state["mem"] = int(psutil.virtual_memory().percent)
        state["disk"] = int(psutil.disk_usage('/').percent)
        boot = time.time() - psutil.boot_time()
        h, m = int(boot//3600), int((boot%3600)//60)
        state["uptime"] = f"{h}h {m}m"
    except Exception as e:
        print(f"[HUD] System error: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(HUD_HTML_PATH, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_404()
        elif self.path == "/api/system":
            self.send_json(state)
        elif self.path == "/api/hud/update":
            self.send_json({"message": state["message"]})
        else:
            self.send_404()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        if self.path == "/api/message":
            state["message"] = body.get('message', '')
            self.send_json({"status": "ok"})
        elif self.path == "/api/command":
            self.send_json({"status": "received"})
        else:
            self.send_404()

    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_404(self):
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def main():
    update_system()
    server = HTTPServer(("", PORT), Handler)
    print(f"[HUD] Server running on http://localhost:{PORT}")
    threading.Thread(target=lambda: [update_system() or time.sleep(2) for _ in iter(int, 1)], daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

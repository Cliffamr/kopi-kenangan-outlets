from http.server import BaseHTTPRequestHandler
import json, os, time, urllib.request

BASE = "https://order.kopikenangan.com/web_order/api"
HEADERS = {"Content-Type": "application/json", "language": "id", "time_zone": "7"}
_last_status = {}

def check_status(code):
    try:
        req = urllib.request.Request(f"{BASE}/store/get_store",
            data=json.dumps({"store_code": code}).encode(), headers=HEADERS)
        r = urllib.request.urlopen(req, timeout=10)
        d = json.loads(r.read())
        if d.get("error_code") == 0:
            return d["data"].get("is_open")
    except Exception:
        pass
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # SSE endpoint - streams store status changes
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Get store codes from query
        parsed = self.path.split('?', 1)
        qs = {}
        if len(parsed) > 1:
            from urllib.parse import parse_qs
            qs = parse_qs(parsed[1])
        codes = qs.get('codes', [''])[0].split(',') if 'codes' in qs else []
        codes = [c.strip() for c in codes if c.strip()][:10]  # Max 10 stores

        if not codes:
            # Send initial ping
            self.wfile.write(f"data: {json.dumps({'type': 'ping', 'msg': 'Send ?codes=CODE1,CODE2 for status updates'})}\n\n".encode())
            self.wfile.flush()
            return

        # Send initial status
        for code in codes:
            is_open = check_status(code)
            if is_open is not None:
                _last_status[code] = is_open
                data = json.dumps({"code": code, "is_open": is_open, "type": "status"})
                self.wfile.write(f"data: {data}\n\n".encode())
        self.wfile.flush()

        # Poll for changes every 60 seconds
        try:
            for _ in range(30):  # 30 iterations × 60s = 30 min max
                time.sleep(60)
                for code in codes:
                    is_open = check_status(code)
                    if is_open is not None and is_open != _last_status.get(code):
                        _last_status[code] = is_open
                        data = json.dumps({"code": code, "is_open": is_open, "type": "change"})
                        self.wfile.write(f"data: {data}\n\n".encode())
                        self.wfile.flush()
                # Keep-alive ping
                self.wfile.write(f"data: {json.dumps({'type': 'ping'})}\n\n".encode())
                self.wfile.flush()
        except Exception:
            pass

    def log_message(self, *a): pass

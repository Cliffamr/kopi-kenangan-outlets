from http.server import BaseHTTPRequestHandler
import json, os, urllib.parse

STORES = None

def load_stores():
    global STORES
    if STORES is None:
        path = os.path.join(os.path.dirname(__file__), '..', 'stores.json')
        with open(path) as f:
            STORES = json.load(f)
    return STORES

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Extract store code from path: /api/stores/STORE_CODE
        code = self.path.split('/api/stores/')[-1].split('?')[0]
        if not code:
            self.send_error(400); return

        # Try local data first
        stores = load_stores()
        store = next((s for s in stores if s['code'] == code), None)

        # If not found, try live API
        if not store:
            try:
                import urllib.request
                r = urllib.request.urlopen(urllib.request.Request(
                    'https://order.kopikenangan.com/web_order/api/store/get_store',
                    data=json.dumps({"store_code": code}).encode(),
                    headers={"Content-Type": "application/json", "language": "id", "time_zone": "7"}
                ))
                d = json.loads(r.read())
                if d.get("error_code") == 0:
                    store = d["data"]
            except Exception:
                pass

        if not store:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Store not found"}).encode())
            return

        body = json.dumps(store, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 's-maxage=60')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

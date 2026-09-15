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
        stores = load_stores()
        parsed = self.path.split('?', 1)
        qs = urllib.parse.parse_qs(parsed[1]) if len(parsed) > 1 else {}

        result = stores
        if 'open' in qs:
            want = qs['open'][0] == '1'
            result = [s for s in result if s.get('is_open') == want]
        if 'q' in qs:
            q = qs['q'][0].lower()
            result = [s for s in result if q in (s.get('name','') + s.get('code','') + s.get('address','')).lower()]
        if 'city' in qs:
            c = qs['city'][0].lower()
            result = [s for s in result if c in (s.get('address','')).lower()]

        body = json.dumps({
            "total": len(stores),
            "open": sum(1 for s in stores if s.get('is_open')),
            "closed": sum(1 for s in stores if not s.get('is_open')),
            "results": len(result),
            "stores": result
        }, ensure_ascii=False).encode()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 's-maxage=300')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

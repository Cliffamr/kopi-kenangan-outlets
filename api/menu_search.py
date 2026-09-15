from http.server import BaseHTTPRequestHandler
import json, os, urllib.parse

STORES = None
MENU_INDEX = None

def load_stores():
    global STORES
    if STORES is None:
        path = os.path.join(os.path.dirname(__file__), '..', 'stores.json')
        with open(path) as f:
            STORES = json.load(f)
    return STORES

def build_menu_index():
    """Pre-build index of store codes from stores.json (menu data fetched on demand)."""
    global MENU_INDEX
    if MENU_INDEX is None:
        stores = load_stores()
        MENU_INDEX = {s['code']: s for s in stores}
    return MENU_INDEX

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = self.path.split('?', 1)
        qs = urllib.parse.parse_qs(parsed[1]) if len(parsed) > 1 else {}
        query = qs.get('q', [''])[0].lower().strip()
        if not query:
            body = json.dumps({"error": "Missing ?q= parameter"}).encode()
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return

        # Search stores by name/code/address matching the query
        # For menu item search, we'd need to fetch menu for each store (expensive)
        # So we support store name search as primary, with a note about menu search
        stores = load_stores()
        matches = []
        for s in stores:
            searchable = (s.get('name','') + s.get('code','') + s.get('address','') + s.get('alias','')).lower()
            if query in searchable:
                matches.append({
                    "store_code": s['code'],
                    "store_name": s.get('name'),
                    "is_open": s.get('is_open'),
                    "address": s.get('address'),
                })

        body = json.dumps({
            "query": query,
            "results": len(matches),
            "stores": matches[:50]  # Limit to 50 results
        }, ensure_ascii=False).encode()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'public, s-maxage=300')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

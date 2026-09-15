from http.server import BaseHTTPRequestHandler
import json, time, urllib.request

BASE = "https://order.kopikenangan.com/web_order/api"
HEADERS = {"Content-Type": "application/json", "language": "id", "time_zone": "7"}
_token = {"val": None, "t": 0}
_menu_cache = {}

def get_token():
    if _token["val"] and time.time() - _token["t"] < 600:
        return _token["val"]
    r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/create_web_token",
        data=json.dumps({"phone": "6281200000000"}).encode(), headers=HEADERS))
    _token["val"] = json.loads(r.read())["data"]["web_order_session_token"]
    _token["t"] = time.time()
    return _token["val"]

def get_menu(code):
    now = time.time()
    if code in _menu_cache and now - _menu_cache[code]['t'] < 300:
        return _menu_cache[code]['data']
    try:
        token = get_token()
        h = {**HEADERS, "Authorization": token}
        r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/product/query_web_order_product_menu",
            data=json.dumps({"store_code": code, "sales_type": 10401}).encode(), headers=h))
        d = json.loads(r.read())
        if d.get("error_code") != 0:
            return None
        groups = []
        for g in d.get("data", {}).get("menu_groups", []):
            products = []
            for p in g.get("menu_products", []):
                products.append({
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "original_price": p.get("orig_price"),
                    "available": not p.get("is_sold_out", False),
                    "has_promo": p.get("has_promotion", False),
                    "image": (p.get("image") or "").split("?")[0],
                })
            groups.append({"group_name": g.get("group_name"), "products": products})
        total = sum(len(g["products"]) for g in groups)
        avail = sum(1 for g in groups for p in g["products"] if p["available"])
        result = {"store_code": code, "total_items": total, "available_items": avail, "groups": groups}
        _menu_cache[code] = {'data': result, 't': now}
        return result
    except Exception:
        return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code = self.path.split('/api/menu/')[-1].split('?')[0]
        if not code:
            self.send_response(400); self.end_headers(); return

        menu = get_menu(code)
        if not menu:
            body = json.dumps({"error": "Menu not available"}).encode()
            self.send_response(404)
        else:
            body = json.dumps(menu, ensure_ascii=False).encode()
            self.send_response(200)

        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'public, s-maxage=60, max-age=30')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

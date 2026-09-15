from http.server import BaseHTTPRequestHandler
import json, os, urllib.request

BASE = "https://order.kopikenangan.com/web_order/api"
HEADERS = {"Content-Type": "application/json", "language": "id", "time_zone": "7"}
_token_cache = {"token": None, "time": 0}

def get_token():
    import time
    if _token_cache["token"] and time.time() - _token_cache["time"] < 600:
        return _token_cache["token"]
    r = urllib.request.urlopen(urllib.request.Request(
        f"{BASE}/create_web_token",
        data=json.dumps({"phone": "6281200000000"}).encode(),
        headers=HEADERS
    ))
    d = json.loads(r.read())
    _token_cache["token"] = d["data"]["web_order_session_token"]
    _token_cache["time"] = time.time()
    return _token_cache["token"]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code = self.path.split('/api/menu/')[-1].split('?')[0]
        if not code:
            self.send_error(400); return
        try:
            token = get_token()
            req = urllib.request.Request(
                f"{BASE}/product/query_web_order_product_menu",
                data=json.dumps({"store_code": code, "sales_type": 10401}).encode(),
                headers={**HEADERS, "Authorization": token}
            )
            r = urllib.request.urlopen(req)
            d = json.loads(r.read())
            if d.get("error_code") != 0:
                raise Exception("API error")

            groups = d.get("data", {}).get("menu_groups", [])
            result = []
            for g in groups:
                products = []
                for p in g.get("menu_products", []):
                    products.append({
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "original_price": p.get("orig_price"),
                        "available": not p.get("is_sold_out", False),
                        "has_promo": p.get("has_promotion", False),
                    })
                result.append({"group_name": g.get("group_name"), "products": products})

            total = sum(len(g["products"]) for g in result)
            avail = sum(1 for g in result for p in g["products"] if p["available"])
            body = json.dumps({
                "store_code": code,
                "total_items": total,
                "available_items": avail,
                "groups": result
            }, ensure_ascii=False).encode()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 's-maxage=60')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, *a): pass

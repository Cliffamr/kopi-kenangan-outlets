from http.server import BaseHTTPRequestHandler
import json, time, urllib.request, urllib.parse, os

BASE = "https://order.kopikenangan.com/web_order/api"
HEADERS = {"Content-Type": "application/json", "language": "id", "time_zone": "7"}
_token = {"val": None, "t": 0}
_opts_cache = {}

def get_token():
    if _token["val"] and time.time() - _token["t"] < 600:
        return _token["val"]
    r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/create_web_token",
        data=json.dumps({"phone": "6281200000000"}).encode(), headers=HEADERS))
    _token["val"] = json.loads(r.read())["data"]["web_order_session_token"]
    _token["t"] = time.time()
    return _token["val"]

def get_options(store_code, product_id):
    """product_id = numeric id from menu API (e.g. 9645), not product_code"""
    now = time.time()
    key = f"{store_code}:{product_id}"
    if key in _opts_cache and now - _opts_cache[key]['t'] < 600:
        return _opts_cache[key]['data']
    try:
        h = {**HEADERS, "Authorization": get_token()}
        r = urllib.request.urlopen(urllib.request.Request(
            f"{BASE}/product/get_web_order_product_options",
            data=json.dumps({"store_code": store_code, "product_id": int(product_id), "sales_type": 10401}).encode(),
            headers=h), timeout=10)
        d = json.loads(r.read())
        if d.get("error_code") != 0:
            return None
        data = d["data"]

        # Dimensions: Temperature, Size, Sugar Level, etc.
        dimensions = []
        for dim in (data.get("product_dimension_wording") or {}).get("dimension_wordings", []):
            dimensions.append({
                "code": dim["dimension_code"],
                "name": dim["dimension_text"],
                "values": [{"id": v["value"], "label": v["value_text"]} for v in dim["dimension_value_wordings"]],
            })

        # Extra notes (Ice Level etc. beyond dimensions)
        notes = []
        for note in data.get("notes", []):
            for g in note.get("groups", []):
                notes.append({
                    "type": note.get("check_type"),
                    "name": g.get("option_name"),
                    "values": dict(zip(g.get("values", []), g.get("value_texts", []))),
                })

        # Combo prices: variant selection -> price (+ addons available)
        opm = data.get("option_product_map") or {}
        variants = {}
        for combo, v in opm.items():
            variants[combo] = {
                "price": v.get("price"),
                "name": v.get("name"),
                "sold_out": bool(v.get("is_sold_out", False)) if v.get("is_sold_out") is not None else False,
                "addons": len(v.get("addon_skus") or []),
            }
        prices = sorted(set(v["price"] for v in variants.values() if v["price"]))

        result = {
            "store_code": store_code,
            "product_id": product_id,
            "name": (data.get("base_product") or {}).get("name"),
            "image": ((data.get("base_product") or {}).get("image") or "").split("?")[0],
            "base_price": (data.get("base_product") or {}).get("price"),
            "prices": prices,
            "dimensions": dimensions,
            "notes": notes,
            "default_selection": data.get("default_selection_impact_sku"),
            "variants": variants,
            "is_sold_out": data.get("is_sold_out", False),
        }
        _opts_cache[key] = {"data": result, "t": now}
        return result
    except Exception as e:
        return {"error": str(e)}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # /api/options/STORE_CODE/PRODUCT_ID
        path = self.path.split('?')[0].rstrip('/')
        qs = urllib.parse.parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        parts = path.split('/')
        # Vercel rewrite may pass /api/options.py — find store/id after 'options'
        nums = [p for p in parts if p.isdigit()]
        alnum = [p for p in parts if p and not p.isdigit() and p not in ('api',) and not p.endswith('.py') and p != 'options']
        store_code = qs.get('store', [None])[0] or (alnum[0] if alnum else None)
        product_id = qs.get('id', [None])[0] or (nums[0] if nums else None)
        if not store_code or not product_id:
            body = json.dumps({"error": "Usage: /api/options/STORE_CODE/PRODUCT_ID (product_id from menu API)"}).encode()
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return
        store_code, product_id = parts[2], parts[3]
        opts = get_options(store_code, product_id)
        if not opts or opts.get("error"):
            body = json.dumps({"error": "Options not available", "detail": opts.get("error") if opts else None}).encode()
            self.send_response(404)
        else:
            body = json.dumps(opts, ensure_ascii=False).encode()
            self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'public, s-maxage=600')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

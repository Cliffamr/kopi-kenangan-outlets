from http.server import BaseHTTPRequestHandler
import json, os, time, urllib.request, urllib.parse

STORES = None
_rt_cache = {}

def load_stores():
    global STORES
    if STORES is None:
        path = os.path.join(os.path.dirname(__file__), '..', 'stores.json')
        with open(path) as f:
            STORES = json.load(f)
    return STORES

def get_realtime(code):
    now = time.time()
    if code in _rt_cache and now - _rt_cache[code]['t'] < 120:
        return _rt_cache[code]['v']
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            'https://order.kopikenangan.com/web_order/api/store/get_store',
            data=json.dumps({"store_code": code}).encode(),
            headers={"Content-Type": "application/json", "language": "id", "time_zone": "7"}
        ))
        d = json.loads(r.read())
        if d.get("error_code") == 0:
            v = d["data"].get("is_open")
            _rt_cache[code] = {"v": v, "t": now}
            return v
    except: pass
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        stores = load_stores()
        parsed = self.path.split('?', 1)
        qs = urllib.parse.parse_qs(parsed[1] if len(parsed) > 1 else "")

        # Get codes to check real-time (comma-separated)
        codes_param = qs.get('codes', [''])[0]
        codes = [c.strip() for c in codes_param.split(',') if c.strip()][:20]

        result = []
        for s in stores:
            entry = {
                "code": s["code"],
                "name": s.get("name"),
                "address": s.get("address"),
                "open": s.get("open"),
                "close": s.get("close"),
                "latitude": s.get("latitude"),
                "longitude": s.get("longitude"),
                "category": s.get("category"),
                "image_url": s.get("image_url"),
                "is_open": s.get("is_open"),  # cached
            }
            # Override with real-time if requested
            if codes and s["code"] in codes:
                rt = get_realtime(s["code"])
                if rt is not None:
                    entry["is_open"] = rt
                    entry["_realtime"] = True
            result.append(entry)

        # Apply filters
        if 'open' in qs:
            want = qs['open'][0] == '1'
            result = [s for s in result if s.get('is_open') == want]
        if 'q' in qs:
            q = qs['q'][0].lower()
            result = [s for s in result if q in (s.get('name','') + s.get('code','') + s.get('address','')).lower()]

        # Distance sort
        if 'lat' in qs and 'lon' in qs:
            import math
            ulat, ulon = float(qs['lat'][0]), float(qs['lon'][0])
            for s in result:
                try:
                    slat, slon = float(s.get('latitude',0)), float(s.get('longitude',0))
                    dlat = math.radians(slat - ulat)
                    dlon = math.radians(slon - ulon)
                    a = math.sin(dlat/2)**2 + math.cos(math.radians(ulat))*math.cos(math.radians(slat))*math.sin(dlon/2)**2
                    s['_dist'] = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                except: s['_dist'] = 9999
            result.sort(key=lambda s: s.get('_dist', 9999))
            for s in result:
                d = s.pop('_dist', None)
                if d is not None and d < 9999:
                    s['distance_km'] = round(d, 1)

        body = json.dumps({
            "total": len(stores),
            "open": sum(1 for s in result if s.get('is_open')),
            "results": len(result),
            "stores": result
        }, ensure_ascii=False).encode()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'public, s-maxage=30')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

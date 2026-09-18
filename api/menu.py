from http.server import BaseHTTPRequestHandler
import json
import re
import time
import urllib.parse

from .transport import BASE, IntegrationError, MAX_BODY_BYTES, REQUEST_TIMEOUT, _open, request_json

HEADERS = {"Content-Type": "application/json", "language": "id", "time_zone": "7"}
_token = {"val": None, "t": 0}
_menu_cache = {}
_MAX_GROUPS = 100
_MAX_PRODUCTS = 200
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]+$")
_URL = re.compile(r"^https://[^/?#]+(?:/[^?#]*)?(?:\?[^#]*)?$")
_STORE = re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$")
_ENVELOPE_KEYS = {"data", "error_code", "msg"}
_TOKEN_ENVELOPE_KEYS = {"data", "error_code", "msg"}
_TOKEN_DATA_KEYS = {"customer_name", "web_order_session_token"}
_DATA_KEYS = {"menu_groups"}
_GROUP_KEYS = {"background_color", "group_code", "group_name", "group_tab_url", "has_combo", "layout_type", "menu_products", "section_icon", "show_promo_only"}
_PRODUCT_KEYS = {"ActionUrl", "active_time", "available_end_timestamp", "brand", "bundle_code", "delivery_restriction", "description", "has_optional_group", "has_promotion", "id", "image", "is_combo_v2", "is_mix_match", "is_restriction_customer", "is_sold_out", "labels", "limit_to_size", "limit_to_skus", "limit_to_temperature", "local_specific_days", "local_time_from", "local_time_to", "local_time_type", "name", "orig_price", "orig_price_dec", "price", "price_dec", "product_code", "product_type_id", "skus", "type_code", "veg_classification"}


def _request_json(path, payload, headers):
    return request_json(path, payload, headers)


def _invalid(message="invalid menu contract"):
    raise ValueError(message)


def _exact_dict(value, keys):
    if type(value) is not dict or set(value) != keys:
        _invalid()
    return value


def _text(value, max_length=300):
    if type(value) is not str or not value or len(value) > max_length or value != value.strip():
        _invalid()
    return value


def _identifier(value):
    if type(value) is int:
        if value < 0:
            _invalid()
        return value
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        _invalid()
    return value


def _sku(value):
    if type(value) is not str or len(value) > 100 or not _IDENTIFIER.fullmatch(value):
        _invalid()
    return value


def _price(value):
    if type(value) is not int or value < 0:
        _invalid()
    return value


def _image(value, optional=False):
    if value is None and optional:
        return ""
    if type(value) is not str or not value or value != value.strip() or not _URL.fullmatch(value):
        _invalid()
    return value.split("?", 1)[0]


def _bool(value):
    if type(value) is not bool:
        _invalid()
    return value


def _product(raw):
    _exact_dict(raw, _PRODUCT_KEYS)
    product_id = _identifier(raw["id"])
    name = _text(raw["name"])
    sku = _sku(raw["product_code"])
    price = _price(raw["price"])
    original_price = _price(raw["orig_price"])
    sold_out = _bool(raw["is_sold_out"])
    promotion = _bool(raw["has_promotion"])
    image = _image(raw["image"], optional=True)
    return {"id": product_id, "sku": sku, "name": name, "price": price, "original_price": original_price, "available": not sold_out, "has_promo": promotion, "image": image}


def _canonical_product(raw):
    identity = str(raw["id"])
    fields = (identity, raw["sku"], raw["name"], raw["price"], raw["original_price"], raw["available"], raw["has_promo"], raw["image"])
    return identity, fields


def _parse_menu(payload, code):
    _exact_dict(payload, _ENVELOPE_KEYS)
    if type(payload["error_code"]) is not int or payload["error_code"] != 0 or type(payload["data"]) is not dict or type(payload["msg"]) is not str:
        _invalid()
    data = _exact_dict(payload["data"], _DATA_KEYS)
    groups_raw = data["menu_groups"]
    if type(groups_raw) is not list or not groups_raw or len(groups_raw) > _MAX_GROUPS:
        _invalid()
    groups = []
    aliases = {}
    sku_aliases = {}
    total = 0
    for group_raw in groups_raw:
        _exact_dict(group_raw, _GROUP_KEYS)
        group_name = _text(group_raw["group_name"])
        group_code = _text(group_raw["group_code"])
        products_raw = group_raw["menu_products"]
        if type(products_raw) is not list or not products_raw or len(products_raw) > _MAX_PRODUCTS:
            _invalid()
        products = []
        for product_raw in products_raw:
            product = _product(product_raw)
            identity, fields = _canonical_product(product)
            if identity in aliases and aliases[identity][0] != fields:
                _invalid("conflicting product alias")
            if product["sku"] in sku_aliases and sku_aliases[product["sku"]][0] != identity:
                _invalid("conflicting SKU alias")
            if identity in aliases:
                continue
            aliases[identity] = (fields, product)
            sku_aliases[product["sku"]] = (identity, product)
            products.append(product)
            total += 1
            if total > _MAX_PRODUCTS:
                _invalid("menu product limit exceeded")
        groups.append({"group_code": group_code, "group_name": group_name, "products": products})
    if total == 0:
        _invalid("empty menu")
    return {"store_code": code, "total_items": total, "available_items": sum(1 for group in groups for product in group["products"] if product["available"]), "groups": groups}


def get_token():
    if _token["val"] is not None and time.time() - _token["t"] < 600:
        return _token["val"]
    payload = _request_json("/create_web_token", json.dumps({"phone": "6281200000000"}).encode(), HEADERS)
    try:
        _exact_dict(payload, _TOKEN_ENVELOPE_KEYS)
        if type(payload["error_code"]) is not int or payload["error_code"] != 0 or type(payload["msg"]) is not str:
            raise IntegrationError("invalid token response")
        data = _exact_dict(payload["data"], _TOKEN_DATA_KEYS)
        if type(data["customer_name"]) is not str:
            raise IntegrationError("invalid token response")
        token = data["web_order_session_token"]
    except (KeyError, TypeError, ValueError):
        raise IntegrationError("invalid token response")
    if type(token) is not str or not token or token != token.strip() or len(token) > 1000:
        raise IntegrationError("invalid token response")
    _token.update(val=token, t=time.time())
    return token


def get_menu(code):
    if type(code) is not str or not _STORE.fullmatch(code):
        return None
    now = time.time()
    if code in _menu_cache and now - _menu_cache[code]["t"] < 300:
        return _menu_cache[code]["data"]
    try:
        payload = _request_json("/product/query_web_order_product_menu", json.dumps({"store_code": code, "sales_type": 10401}).encode(), {**HEADERS, "Authorization": get_token()})
        result = _parse_menu(payload, code)
    except (IntegrationError, ValueError, TypeError, KeyError):
        return None
    _menu_cache[code] = {"data": result, "t": now}
    return result


def _route(path):
    prefix = "/api/menu/" if path.startswith("/api/menu/") else "/api/menu.py/"
    if not path.startswith(prefix) or path.endswith("/") or path.count("/") != 3:
        return None
    code = path[len(prefix):]
    return code if _STORE.fullmatch(code) else None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        code = _route(parsed.path) if not parsed.query else None
        if code is None:
            body = json.dumps({"error": "invalid menu route"}).encode()
            self.send_response(400)
        else:
            menu = get_menu(code)
            if not menu:
                body = json.dumps({"error": "Menu not available"}).encode()
                self.send_response(404)
            else:
                body = json.dumps(menu, ensure_ascii=False).encode()
                self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, s-maxage=60, max-age=30")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

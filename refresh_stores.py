#!/usr/bin/env python3
"""
Refresh stores.json from Kopi Kenangan API.
Run as cron job (Vercel Cron or GitHub Actions).

Usage:
  python3 refresh_stores.py           # Refresh and save
  python3 refresh_stores.py --dry-run # Preview without saving
"""
import json, time, urllib.request, argparse

BASE = "https://order.kopikenangan.com/web_order/api"
HEADERS = {"Content-Type": "application/json", "language": "id", "time_zone": "7"}

def fetch_all_stores():
    all_stores = []
    page = 1
    while True:
        try:
            req = urllib.request.Request(f"{BASE}/store/query_store",
                data=json.dumps({"page_num": page, "page_size": 10}).encode(),
                headers=HEADERS)
            r = urllib.request.urlopen(req, timeout=15)
            d = json.loads(r.read())
            if d.get("error_code") != 0:
                break
            data = d["data"]
            stores = data.get("store", [])
            all_stores.extend(stores)
            print(f"\r  Page {page}/{data.get('pages',1)} ({len(all_stores)} stores)", end="", flush=True)
            if page >= data.get("pages", 1):
                break
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"\n  Error on page {page}: {e}")
            break
    print()
    return all_stores

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", default="stores.json")
    args = ap.parse_args()

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Refreshing stores...")
    stores = fetch_all_stores()
    print(f"  Fetched {len(stores)} stores")

    if args.dry_run:
        open_count = sum(1 for s in stores if s.get("is_open"))
        print(f"  Open: {open_count}, Closed: {len(stores) - open_count}")
        return

    with open(args.output, "w") as f:
        json.dump(stores, f, ensure_ascii=False)
    print(f"  Saved to {args.output} ({len(stores)} stores)")

if __name__ == "__main__":
    main()

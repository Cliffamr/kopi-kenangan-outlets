#!/usr/bin/env python3
"""
Refresh stores.json from jasdorkopi.id API (1337+ stores).
Run as cron job or manually.

Usage:
  python3 refresh_stores.py           # Refresh from jasdorkopi.id
  python3 refresh_stores.py --dry-run # Preview without saving
"""
import json, time, urllib.request, argparse

def fetch_all_stores():
    all_outlets = []
    page = 1
    while True:
        try:
            r = urllib.request.urlopen(f'https://jasdorkopi.id/api/outlets?page={page}')
            d = json.loads(r.read())
            outlets = d.get('data', [])
            if not outlets:
                break
            all_outlets.extend(outlets)
            meta = d.get('meta', {})
            last = meta.get('last_page', 1)
            print(f"\r  Page {page}/{last} ({len(all_outlets)}/{meta.get('total','?')})", end="", flush=True)
            if page >= last:
                break
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"\n  Error on page {page}: {e}")
            break
    print()
    return all_outlets

def convert(outlets):
    stores = []
    for o in outlets:
        stores.append({
            'code': o.get('code'),
            'name': o.get('name'),
            'address': o.get('address'),
            'latitude': str(o.get('latitude', '')),
            'longitude': str(o.get('longitude', '')),
            'is_open': o.get('is_open', False),
            'open': o.get('open_time', ''),
            'close': o.get('order_close_time', o.get('real_close_time', '')),
            'category': o.get('category', ''),
            'image_url': o.get('image_url', ''),
            'brand_and_image': [{'brand_name': 'Kopi Kenangan'}],
        })
    return stores

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", default="stores.json")
    args = ap.parse_args()

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Refreshing stores from jasdorkopi.id...")
    outlets = fetch_all_stores()
    stores = convert(outlets)
    open_c = sum(1 for s in stores if s.get('is_open'))
    print(f"  {len(stores)} stores ({open_c} open)")

    if args.dry_run:
        return

    with open(args.output, "w") as f:
        json.dump(stores, f, ensure_ascii=False)
    print(f"  Saved to {args.output}")

if __name__ == "__main__":
    main()

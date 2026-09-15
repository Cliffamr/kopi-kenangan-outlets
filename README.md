# ☕ Kopi Kenangan — Outlet & Menu API

Unofficial real-time API for [Kopi Kenangan](https://kopikenangan.com) outlets and menus. Data sourced from `order.kopikenangan.com` web ordering platform.

> ⚠️ **Disclaimer**: Ini proyek riset pribadi. Tidak berafiliasi dengan Kopi Kenangan. Gunakan secara bertanggung jawab.

## Live Demo

🔗 **[kopi-kenangan-outlets.vercel.app](https://kopi-kenangan-outlets.vercel.app)**

## Features

- 🏪 **1,340+ outlets** — semua brand (Kopi Kenangan, Chigo, Kenangan Heritage, Flip Burger, dll)
- 🟢 **Status real-time** — buka/tutup berdasarkan jam operasional
- 🍵 **Menu lengkap** — nama, harga, promo, ketersediaan item
- 📍 **Location-aware** — sort by jarak dari lokasi user
- 🔍 **Search** — cari outlet atau menu item
- ⚡ **Fast** — Vercel edge caching, auto-refresh
- 📱 **Mobile-first** — responsive UI

## API Endpoints

### `GET /api/stores`

List semua outlet.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lat` | float | Latitude user (untuk distance sort) |
| `lon` | float | Longitude user |
| `q` | string | Search (nama, kode, alamat) |
| `open` | 0/1 | Filter buka/tutup |
| `city` | string | Filter kota |

**Response:**
```json
{
  "total": 1340,
  "open": 487,
  "closed": 853,
  "results": 10,
  "stores": [
    {
      "code": "LIPPO-PURI",
      "name": "Lippo Mall Puri",
      "address": "Lippo Mall Puri, Jakarta Barat",
      "is_open": false,
      "open": "10:00:00",
      "close": "21:45:00",
      "latitude": "-6.18981100",
      "longitude": "106.73901400",
      "brand_and_image": [{"brand_name": "Kopi Kenangan"}],
      "category": "Mall",
      "distance_km": 3.2
    }
  ]
}
```

### `GET /api/stores/:code`

Detail 1 outlet + **real-time status** (live check ke server).

**Response:**
```json
{
  "code": "DPK.APTKROXY",
  "name": "Apotik Roxy Depok",
  "is_open": true,
  "open": "00:01:00",
  "close": "23:49:00",
  "address": "Apotek Roxy Nusantara Depok...",
  "latitude": "-6.39182200",
  "longitude": "106.82457100"
}
```

### `GET /api/menu/:code`

Menu outlet — nama, harga, promo, ketersediaan.

**Response:**
```json
{
  "store_code": "DPK.APTKROXY",
  "total_items": 96,
  "available_items": 94,
  "groups": [
    {
      "group_name": "Coffee",
      "products": [
        {
          "name": "Kopi Kenangan Mantan",
          "price": 19000,
          "original_price": 22000,
          "available": true,
          "has_promo": true
        }
      ]
    }
  ]
}
```

### `GET /api/menu/search?q=kopi`

Cari outlet yang menjual item tertentu.

**Response:**
```json
{
  "query": "kopi",
  "results": 89,
  "stores": [
    {
      "store_code": "DPK.APTKROXY",
      "store_name": "Apotik Roxy Depok",
      "matching_items": ["Kopi Kenangan Mantan", "Kopi Kenangan Hazelnut"]
    }
  ]
}
```

### `GET /api/stream/status`

SSE (Server-Sent Events) stream untuk status outlet real-time.

## Quick Start

### Deploy to Vercel

1. Fork repo ini
2. Buka [vercel.com/new](https://vercel.com/new)
3. Import repo → Deploy
4. Selesai! Dapat URL `your-project.vercel.app`

### Local Development

```bash
git clone https://github.com/Cliffamr/kopi-kenangan-outlets.git
cd kopi-kenangan-outlets
python3 api/stores.py  # Server di http://localhost:8000
```

### Usage Examples

```bash
# Semua outlet buka
curl https://your-app.vercel.app/api/stores?open=1

# Outlet terdekat Jakarta
curl "https://your-app.vercel.app/api/stores?lat=-6.200&lon=106.816"

# Search outlet
curl "https://your-app.vercel.app/api/stores?q=bandung"

# Real-time status 1 outlet
curl https://your-app.vercel.app/api/stores/LIPPO-PURI

# Menu outlet
curl https://your-app.vercel.app/api/menu/DPK.APTKROXY

# Cari outlet yang jual "Kopi Kenangan Mantan"
curl "https://your-app.vercel.app/api/menu/search?q=kopi+kenangan+mantan"
```

## Tech Stack

- **Backend:** Python (stdlib http.server) — zero dependencies
- **Frontend:** Vanilla HTML/CSS/JS — zero build step
- **Hosting:** Vercel Serverless Functions
- **Data:** `order.kopikenangan.com` web API
- **Cache:** In-memory TTL cache + Vercel edge caching

## Data Source

Semua data dari web ordering platform `order.kopikenangan.com`:
- `/store/query_store` — bulk outlet list (public)
- `/store/get_store` — real-time status (public)
- `/product/query_web_order_product_menu` — menu (free web token)

## Project Structure

```
├── api/
│   ├── stores.py           # GET /api/stores — list + search + sort
│   ├── store_detail.py     # GET /api/stores/:code — real-time status
│   ├── menu.py             # GET /api/menu/:code — menu items
│   ├── menu_search.py      # GET /api/menu/search — find by item
│   └── stream_status.py    # GET /api/stream/status — SSE updates
├── stores.json             # Cached 1340 outlets (auto-refresh)
├── refresh_stores.py       # Cron script to update stores.json
├── index.html              # Frontend UI
├── vercel.json             # Vercel config
└── README.md
```

## Brand List

| Brand | Code |
|-------|------|
| Kopi Kenangan | 1 |
| Chigo | 4 |
| Kenangan Heritage | 6 |
| Chigo x Flip | 8 |
| Flip Burger | 9 |
| Kenangan Signature | 10 |

## License

MIT — data publik, dokumentasi komunitas.

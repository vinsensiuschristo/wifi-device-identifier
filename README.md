# WiFi Device Identifier

Aplikasi Python (Flask) untuk mengidentifikasi perangkat user yang login ke WiFi provider melalui parsing User-Agent header. **🧠 Smart Scraper**: Scraping harga pasar wajar dari Tokopedia dengan metodologi statistik profesional!

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone & Setup
git clone https://github.com/vinsensiuschristo/wifi-device-identifier.git
cd wifi-device-identifier

# Virtual Environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install Dependencies
pip install -r requirements.txt

# Run
python main.py
```

Aplikasi: **http://localhost:5000**

---

## 🧠 Smart Price Scraper (Fitur Utama!)

Bukan scraper biasa! Menggunakan metodologi statistik untuk mendapatkan **Harga Pasar Wajar**.

### Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. URL SMART FILTER                                                 │
│     • condition = NEW (baru saja)                                   │
│     • seller = Official Store + Power Merchant                      │
│     • sort = Ulasan Terbanyak (bukan harga terendah!)               │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  2. SAMPLING                                                         │
│     Ambil 10-20 harga dari toko terpercaya                          │
│     Raw: [3.2jt, 4.5jt, 8.4jt, 8.5jt, 8.5jt, 8.6jt, 8.7jt, 11jt]   │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  3. GAP-BASED CLUSTER DETECTION (Kunci!)                             │
│     Deteksi cluster berdasarkan GAP (jarak antar nilai):            │
│                                                                      │
│     Gaps: 3.2→4.5(1.3) 4.5→8.4(3.9!) 8.4→8.5(0.1) ... 8.7→11(2.3!) │
│                              ↑ GAP BESAR            ↑ GAP BESAR     │
│                                                                      │
│     Cluster 1: [3.2, 4.5]               → 2 items                   │
│     Cluster 2: [8.4, 8.5, 8.5, 8.6, 8.7] → 5 items ← TERBESAR!      │
│     Cluster 3: [11, 11.5, 12]           → 3 items                   │
│                                                                      │
│     Ambil cluster TERBESAR, buang sisanya sebagai outlier!          │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  4. AVERAGE CALCULATION                                              │
│     Rata-rata dari cluster terbesar (outlier sudah dibuang)         │
│     (8.4 + 8.5 + 8.5 + 8.6 + 8.7) / 5 = 8.54jt                     │
│     Result: Rp 8.540.000 ← Harga Pasar Wajar                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Kenapa Gap-Based Cluster Detection?

```
Raw: [3.2jt, 4.5jt, 8.4jt, 8.5jt, 8.5jt, 8.6jt, 8.7jt, 11jt, 11.5jt, 12jt]

Gap Analysis:
  3.2 → 4.5  = 1.3jt
  4.5 → 8.4  = 3.9jt  ← GAP BESAR! (pisahkan cluster)
  8.4 → 8.5  = 0.1jt  ← Cluster (rapat)
  8.5 → 8.5  = 0.0jt  ← Cluster
  8.5 → 8.6  = 0.1jt  ← Cluster
  8.6 → 8.7  = 0.1jt  ← Cluster
  8.7 → 11   = 2.3jt  ← GAP BESAR! (pisahkan cluster)
  11 → 11.5  = 0.5jt
  11.5 → 12  = 0.5jt

Cluster terbesar: [8.4, 8.5, 8.5, 8.6, 8.7] (5 items)
Outlier dibuang: [3.2, 4.5, 11, 11.5, 12]

AVERAGE = (8.4+8.5+8.5+8.6+8.7)/5 = 8.54jt ← Harga Pasar Wajar!
```

### ⚡ Performa (Optimized)

| Operasi | Kompleksitas |
|---------|--------------|
| Sort data | O(n log n) |
| Gap calculation | O(n) |
| Cluster detection | O(n) |
| Average | O(n) |
| **Total** | **O(n log n)** |

Sangat cepat untuk data 10-100 harga per produk!

### Confidence Levels

| Level | Samples | Arti |
|-------|---------|------|
| 🟢 HIGH | ≥10 | Sangat reliable |
| 🟡 MEDIUM | 5-9 | Cukup reliable |
| 🔴 LOW | <5 | Mungkin kurang akurat |

---

## 📋 Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/login` | GET/POST | Captive portal |
| `/dashboard` | GET | Admin dashboard |
| `/api/scrape-price/<device>` | GET | 🧠 Manual Smart Scraping |
| `/api/scraper-cache/clear` | POST | Clear cache |
| `/api/devices` | GET | All devices JSON |
| `/api/report` | GET | Statistics JSON |
| `/api/export/csv` | GET | Export CSV |

### Contoh API

```bash
curl "http://localhost:5000/api/scrape-price/Samsung%20Galaxy%20S24"
```

Response:
```json
{
  "success": true,
  "device": "Samsung Galaxy S24",
  "price": {
    "market_price": 14500000,
    "min": 14000000,
    "max": 15500000
  },
  "confidence": "high",
  "samples": 12
}
```

---

## 📁 Structure

```
wifi-device-identifier/
├── main.py
├── config.py
├── requirements.txt
├── app/
│   ├── routes.py          # All endpoints
│   ├── user_agent.py      # UA parser
│   └── templates/
├── database/
│   ├── device_db.py       # CSV database
│   └── models.py          # SQLite models
├── scraper/               # 🧠 Smart Scraper
│   └── price_scraper.py   # Tokopedia scraper
└── data/
    ├── devices.csv
    └── prices.csv
```
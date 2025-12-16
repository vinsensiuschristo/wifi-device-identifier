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
│     Raw: [4.5jt, 8.4jt, 8.5jt, 8.5jt, 8.6jt, 8.7jt, 11jt]          │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  3. DATA CLEANING (Kunci!)                                           │
│     Buang 15% TERMURAH → Flash Sale, Promo, Penipuan                │
│     Buang 15% TERMAHAL → Overprice, Stok lama                       │
│     Sisa: [8.4jt, 8.5jt, 8.5jt, 8.6jt, 8.7jt]                       │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  4. MEDIAN CALCULATION                                               │
│     Menggunakan MEDIAN (bukan rata-rata!)                           │
│     Result: Rp 8.500.000 ← Harga Pasar Wajar                        │
│     Confidence: HIGH (10+ samples)                                   │
└──────────────────────────────────────────────────────────────────────┘
```

### Kenapa MEDIAN bukan AVERAGE?

```
Data: [1jt, 8jt, 8jt, 8jt, 20jt]

AVERAGE = 9jt   ← Terdistorsi oleh 1jt dan 20jt!
MEDIAN  = 8jt   ← Stabil, tidak terpengaruh outlier
```

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

---

## ⚠️ Notes untuk Intern

1. **Rate Limiting**: 2 detik antar request (jangan sampai kena ban IP kantor!)
2. **Caching**: 1 jam untuk efisiensi
3. **Fallback**: Kalau scraping gagal → pakai harga database CSV

### Bisa Dijelaskan ke Atasan:

> "Saya menggunakan metodologi Smart Scraper dengan:
> - URL filtering ke Official Store & Power Merchant untuk validitas
> - Statistical cleaning untuk membuang outlier (promo/overprice)
> - Median calculation yang lebih robust daripada rata-rata"

---

## 📄 License

MIT License

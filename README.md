# WiFi Device Identifier

Aplikasi Python (Flask) untuk mengidentifikasi perangkat user yang login ke WiFi provider melalui parsing User-Agent header. **Fitur baru**: Scraping harga perangkat dari Tokopedia secara otomatis!

## 🚀 Quick Start

### Prerequisites
- Python 3.10 atau lebih baru
- pip (Python package manager)

### Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/vinsensiuschristo/wifi-device-identifier.git
   cd wifi-device-identifier
   ```

2. **Buat virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
python main.py
```

Aplikasi akan berjalan di: **http://localhost:5000**

---

## 📱 Alur Kerja Aplikasi (Application Flow)

Berikut adalah penjelasan lengkap bagaimana aplikasi ini bekerja:

### 1️⃣ User Connect ke WiFi
```
[User] --> [Connect WiFi] --> [Redirect ke Captive Portal]
```
Ketika user mencoba terhubung ke WiFi, router akan mengarahkan mereka ke halaman login (captive portal).

### 2️⃣ Login Page (GET /login)
```
[Server] --> [Send Login Page]
         --> [Request Client Hints via Headers]
```
Server mengirim halaman login dan meminta browser untuk mengirim **Client Hints** - informasi tambahan tentang device yang lebih akurat dari User-Agent.

### 3️⃣ User Submit Form (POST /login)
```
[User Submit] --> [Browser sends User-Agent + Client Hints]
```
Saat user submit form, browser mengirim:
- **User-Agent**: String yang berisi info device (contoh: `Mozilla/5.0 (Linux; Android 14; SM-S911B)...`)
- **Client Hints**: Header tambahan seperti `Sec-CH-UA-Model: "SM-S911B"`

### 4️⃣ Parse User-Agent
```
[Server] --> [UserAgentParser] --> Extract:
         - model_code: SM-S911B
         - os_type: android
         - os_version: 14
         - browser: Chrome
```
Sistem mem-parse User-Agent untuk mengekstrak informasi device.

### 5️⃣ Cari Device di Database
```
[model_code: SM-S911B] --> [devices.csv] --> {
    brand: "Samsung",
    marketing_name: "Galaxy S24",
    price_idr: 15000000
}
```
Kode model dicari di database CSV untuk mendapatkan nama marketing dan harga.

### 6️⃣ 🆕 Scraping Harga dari Tokopedia
```
[Device Found] --> [TokopediaScraper] --> Search: "Samsung Galaxy S24"
                                      --> Extract price range dari hasil
                                      --> Return: min: 14.5jt, max: 16jt
```
**FITUR BARU!** Jika device ditemukan, sistem akan otomatis mencari harga di Tokopedia untuk mendapatkan range harga terkini.

### 7️⃣ Simpan ke Database
```
[All Data] --> [SQLite Database] --> login_logs table
```
Semua informasi disimpan ke database SQLite termasuk:
- Username, IP address
- Device info (brand, model, marketing name)
- Harga dari database dan harga dari Tokopedia
- URL Tokopedia untuk referensi

### 8️⃣ Dashboard Report
```
[Admin] --> [/dashboard] --> View:
        - Total logins
        - Unique devices
        - Price estimates
        - Tokopedia price comparison
```
Admin bisa melihat semua data di dashboard lengkap dengan link ke Tokopedia.

---

## 📊 Diagram Alur Lengkap

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WiFi DEVICE IDENTIFIER FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐         ┌──────────────┐         ┌──────────────────┐
    │   User   │ ──WiFi──▶ │ Captive      │ ──GET──▶ │ /login          │
    │  Device  │         │  Portal       │         │ (Show Form)     │
    └──────────┘         └──────────────┘         └──────────────────┘
         │                                                  │
         │                                                  ▼
         │                                         ┌──────────────────┐
         └───────────── Submit Form ─────────────▶│ POST /login      │
                         (Username)                │ + User-Agent     │
                                                   │ + Client Hints   │
                                                   └────────┬─────────┘
                                                            │
              ┌─────────────────────────────────────────────┘
              ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ UserAgentParser │───▶│  DeviceDatabase │───▶│TokopediaScraper │
    │                 │    │   (devices.csv) │    │  (Harga Online) │
    │ Extract:        │    │                 │    │                 │
    │ - model_code    │    │ Match:          │    │ Scrape:         │
    │ - os_type       │    │ - brand         │    │ - min_price     │
    │ - browser       │    │ - marketing_name│    │ - max_price     │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
              │                    │                      │
              └────────────────────┼──────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────┐
                         │  LoginDatabase  │
                         │    (SQLite)     │
                         │                 │
                         │ Store:          │
                         │ - user info     │
                         │ - device info   │
                         │ - db price      │
                         │ - scraped price │
                         │ - tokopedia url │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌───────────┐ ┌───────────┐ ┌───────────────┐
            │ Dashboard │ │ API JSON  │ │ Export CSV/   │
            │ (HTML)    │ │ Endpoints │ │ JSON Reports  │
            └───────────┘ └───────────┘ └───────────────┘
```

---

## 📋 Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/login` | GET/POST | Captive portal login (capture User-Agent) |
| `/dashboard` | GET | Admin dashboard & reports |
| `/api/devices` | GET | API data devices yang login |
| `/api/report` | GET | API report statistik |
| `/api/test-ua` | GET | Test User-Agent parsing |
| `/api/export/csv` | GET | Export data ke CSV |
| `/api/export/json` | GET | Export data ke JSON |
| `/api/scrape-price/<device>` | GET | 🆕 Manual scraping harga |
| `/api/scraper-cache/clear` | POST | 🆕 Clear cache scraper |
| `/api/clear-logs` | POST | Hapus semua logs |

---

## 📁 Project Structure

```
wifi-device-identifier/
├── main.py              # Entry point aplikasi
├── config.py            # Konfigurasi aplikasi
├── requirements.txt     # Python dependencies
│
├── app/                 # Application modules
│   ├── __init__.py
│   ├── routes.py        # Route definitions (dengan comments lengkap)
│   ├── user_agent.py    # User-Agent parser
│   └── templates/       # HTML templates
│       ├── login.html
│       ├── login_success.html
│       └── dashboard.html
│
├── database/            # Database modules
│   ├── __init__.py
│   ├── device_db.py     # Device database (CSV)
│   └── models.py        # SQLite models
│
├── scraper/             # 🆕 Price scraping modules
│   ├── __init__.py
│   └── price_scraper.py # Tokopedia price scraper
│
├── data/                # Data files
│   ├── devices.csv      # Device database
│   └── prices.csv       # Price database
│
├── output/              # Generated exports
└── reports/             # Report generator
```

---

## 🆕 Fitur Price Scraping

### Cara Kerja
1. Saat device teridentifikasi, sistem membuat query pencarian (contoh: "Samsung Galaxy S24")
2. Query dikirim ke Tokopedia search page
3. Hasil HTML di-parse untuk extract harga
4. Harga di-cache selama 1 jam untuk mengurangi request
5. Range harga (min-max) ditampilkan di dashboard

### Catatan Penting
- **Rate Limiting**: Request dibatasi 1 per detik untuk menghindari blocking
- **Caching**: Hasil di-cache 1 jam untuk efisiensi
- **Fallback**: Jika scraping gagal, harga dari database lokal digunakan
- **Legal**: Pastikan penggunaan sesuai dengan ToS Tokopedia

### Manual Scraping
Anda bisa test scraping manual via API:
```bash
curl "http://localhost:5000/api/scrape-price/Samsung%20Galaxy%20S24"
```

Response:
```json
{
  "success": true,
  "device": "Samsung Galaxy S24",
  "price": {
    "min": 14500000,
    "max": 16000000,
    "avg": 15250000,
    "product_count": 25
  },
  "tokopedia_url": "https://tokopedia.com/search?q=..."
}
```

---

## 📊 Data Format

### devices.csv
```csv
Brand,Model_Code,Marketing_Name
Samsung,SM-S911B,Samsung Galaxy S23
Xiaomi,2201117TG,Xiaomi 12
```

### prices.csv
```csv
Brand,Marketing_Name,Price_IDR,Year
Samsung,Samsung Galaxy S23,12000000,2025
```

---

## 🔧 Configuration

Edit `config.py` untuk mengubah konfigurasi:
- `SECRET_KEY` - Flask secret key
- `DEBUG` - Debug mode (True/False)

---

## 👥 Team

Untuk kontribusi, silakan buat branch baru dan submit pull request.

---

## 📄 License

MIT License

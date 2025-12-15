# WiFi Device Identifier

Aplikasi Python (Flask) untuk mengidentifikasi perangkat user yang login ke WiFi provider melalui parsing User-Agent header.

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

## 📋 Endpoints

| Endpoint | Deskripsi |
|----------|-----------|
| `/login` | Captive portal login (capture User-Agent) |
| `/dashboard` | Admin dashboard & reports |
| `/api/devices` | API data devices yang login |
| `/api/report` | API report statistik |
| `/api/test-ua` | Test User-Agent parsing |

## 📁 Project Structure

```
wifi-device-identifier/
├── main.py              # Entry point aplikasi
├── config.py            # Konfigurasi aplikasi
├── requirements.txt     # Python dependencies
├── app/                 # Application modules
│   ├── routes.py        # Route definitions
│   ├── templates/       # HTML templates
│   └── static/          # CSS, JS, images
├── data/                # Data files (devices.csv, prices.csv)
├── database/            # Database files
├── output/              # Output files
└── reports/             # Generated reports
```

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

## 🔧 Configuration

Edit `config.py` untuk mengubah konfigurasi:
- `SECRET_KEY` - Flask secret key
- `DEBUG` - Debug mode (True/False)

## 👥 Team

Untuk kontribusi, silakan buat branch baru dan submit pull request.

## 📄 License

MIT License

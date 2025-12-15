# WiFi Device Identifier

Aplikasi Python (Flask) untuk mengidentifikasi perangkat user yang login ke WiFi provider melalui parsing User-Agent header.

## Instalasi

```bash
cd wifi-device-identifier
pip install -r requirements.txt
```

## Menjalankan Aplikasi

```bash
python main.py
```

Akses di browser: http://localhost:5000

## Endpoints

- `/login` - Captive portal login (capture User-Agent)
- `/dashboard` - Admin dashboard & reports
- `/api/devices` - API data devices yang login
- `/api/report` - API report statistik

## Struktur Data

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

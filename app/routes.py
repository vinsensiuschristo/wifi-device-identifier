"""
=============================================================================
FLASK ROUTES - WiFi Device Identifier
=============================================================================

File ini mengatur semua route/endpoint untuk aplikasi WiFi Device Identifier.
Ini adalah "otak" dari aplikasi yang menghubungkan berbagai komponen.

ALUR UTAMA APLIKASI:
====================
1. User konek ke WiFi → Browser redirect ke /login (Captive Portal)
2. User submit form login → Server capture User-Agent
3. User-Agent diparse untuk extract info device
4. Device dicari di database untuk mendapatkan nama marketing & harga
5. Jika device ditemukan, scraping harga dari Tokopedia
6. Semua data disimpan ke database SQLite
7. Admin bisa lihat statistik di /dashboard

ENDPOINT YANG TERSEDIA:
=======================
- GET  /           → Redirect ke login page
- GET  /login      → Tampilkan form login
- POST /login      → Process login, identify device, scrape price
- GET  /dashboard  → Admin dashboard dengan statistik
- GET  /api/devices → JSON all devices
- GET  /api/report  → JSON report summary
- GET  /api/export/<format> → Export data ke CSV/JSON
- GET  /api/scrape-price/<device> → Manual price scraping
- POST /api/clear-logs → Hapus semua logs

Author: WiFi Device Identifier Team
Created: December 2025
=============================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, make_response
import os
import sys

# Tambahkan parent directory ke path agar bisa import module lokal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import module-module lokal
from app.user_agent import UserAgentParser           # Parser untuk User-Agent
from database.device_db import DeviceDatabase        # Database device dari CSV
from database.models import LoginDatabase            # Database SQLite untuk logs
from reports.generator import ReportGenerator       # Generator laporan
from scraper.price_scraper import TokopediaScraper  # Scraper harga Tokopedia
import config

# =============================================================================
# INISIALISASI KOMPONEN
# =============================================================================

# Parser User-Agent - mengubah raw User-Agent string menjadi info device
ua_parser = UserAgentParser()

# Database device - berisi daftar device dari CSV (Brand, Model, Marketing Name)
device_db = DeviceDatabase(config.DEVICES_CSV, config.PRICES_CSV)

# Database login - SQLite untuk menyimpan log login
login_db = LoginDatabase(config.DATABASE_PATH)

# Report generator - untuk export data
report_gen = ReportGenerator(login_db)

# Tokopedia scraper - untuk mencari harga device online
# FITUR BARU: Scraping harga dari Tokopedia
tokopedia_scraper = TokopediaScraper()

print("[Routes] All components initialized")

# Buat Flask Blueprint
main = Blueprint('main', __name__)


@main.route('/')
def index():
    """
    Root route - redirect ke halaman login
    
    Ketika user membuka http://server-ip/, mereka akan
    otomatis diarahkan ke halaman login captive portal.
    """
    return redirect(url_for('main.login'))


@main.route('/login', methods=['GET', 'POST'])
def login():
    """
    ========================================================================
    CAPTIVE PORTAL LOGIN PAGE - Endpoint utama untuk identifikasi device
    ========================================================================
    
    Ini adalah endpoint paling penting dalam aplikasi!
    
    CARA KERJA:
    -----------
    GET Request:
        1. User membuka halaman login
        2. Server mengirim header untuk request Client Hints
        3. Browser menampilkan form login
    
    POST Request (saat user submit form):
        1. Ambil username dan password dari form
        2. Capture User-Agent string dari browser
        3. Capture Client Hints (jika browser support)
        4. Parse User-Agent untuk extract info device
        5. Cari device di database lokal
        6. Jika device ditemukan, scrape harga dari Tokopedia
        7. Simpan semua data ke database SQLite
        8. Tampilkan halaman sukses dengan info device
    
    CLIENT HINTS:
    -------------
    Chrome 90+ mengirim header tambahan yang lebih akurat:
    - Sec-CH-UA-Model: Model device (contoh: "SM-S911B")
    - Sec-CH-UA-Platform: OS (contoh: "Android")
    - Sec-CH-UA-Platform-Version: Versi OS
    - Sec-CH-UA-Mobile: Apakah mobile device
    """
    
    # ==========================================================================
    # POST REQUEST: Process login dan identify device
    # ==========================================================================
    if request.method == 'POST':
        
        # ----------------------------------------------------------------------
        # STEP 1: Ambil data dari form login
        # ----------------------------------------------------------------------
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        print(f"\n[Login] === New Login Request ===")
        print(f"[Login] Username: {username}")
        
        # ----------------------------------------------------------------------
        # STEP 2: Capture User-Agent dan IP Address
        # ----------------------------------------------------------------------
        # User-Agent adalah string yang dikirim browser yang berisi info device
        # Contoh: "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36..."
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        
        print(f"[Login] IP: {ip_address}")
        print(f"[Login] User-Agent: {user_agent[:100]}...")
        
        # ----------------------------------------------------------------------
        # STEP 3: Capture Client Hints (fitur browser modern)
        # ----------------------------------------------------------------------
        # Client Hints lebih akurat daripada User-Agent untuk identifikasi device
        # Tapi tidak semua browser support (Chrome 90+, Edge 90+)
        ch_model = request.headers.get('Sec-CH-UA-Model', '')
        ch_platform = request.headers.get('Sec-CH-UA-Platform', '')
        ch_platform_version = request.headers.get('Sec-CH-UA-Platform-Version', '')
        ch_mobile = request.headers.get('Sec-CH-UA-Mobile', '')
        ch_full_version = request.headers.get('Sec-CH-UA-Full-Version-List', '')
        
        if ch_model:
            print(f"[Login] Client Hints Model: {ch_model}")
        
        # ----------------------------------------------------------------------
        # STEP 4: Parse User-Agent untuk extract informasi device
        # ----------------------------------------------------------------------
        # UserAgentParser akan mengekstrak:
        # - model_code: Kode model device (SM-S911B, iPhone15,3, dll)
        # - os_type: android, ios, windows, dll
        # - os_version: Versi OS
        # - browser: Chrome, Safari, Firefox, dll
        parsed = ua_parser.parse(user_agent)
        
        # Jika ada Client Hints, override model_code karena lebih akurat
        if ch_model and ch_model.strip('"'):
            parsed.model_code = ch_model.strip('"')
        
        print(f"[Login] Parsed - Model: {parsed.model_code}, OS: {parsed.os_type} {parsed.os_version}")
        
        # ----------------------------------------------------------------------
        # STEP 5: Cari device di database lokal
        # ----------------------------------------------------------------------
        # Database berisi mapping model_code -> (brand, marketing_name, price)
        # Contoh: "SM-S911B" -> ("Samsung", "Galaxy S24", 15000000)
        device = None
        
        # Kumpulkan semua kemungkinan model code
        model_codes = [parsed.model_code] if parsed.model_code else []
        model_codes.extend(ua_parser.extract_model_codes(user_agent))
        
        # Coba cari di database (exact match only)
        for code in model_codes:
            # Skip placeholder yang tidak valid
            if code and code != 'K' and code != 'Android Device':
                device = device_db.find_device(code)
                if device:
                    print(f"[Login] Device found: {device.brand} {device.marketing_name}")
                    break
        
        if not device:
            print(f"[Login] Device not found in database")
        
        # ----------------------------------------------------------------------
        # STEP 6: FITUR BARU - Scraping harga dari Tokopedia
        # ----------------------------------------------------------------------
        # Jika device ditemukan, cari harga di Tokopedia untuk perbandingan
        scraped_price_min = None
        scraped_price_max = None
        price_source = 'none'
        tokopedia_url = None
        
        if device and device.marketing_name:
            # Buat query pencarian dengan format: "Brand MarketingName"
            # Contoh: "Samsung Galaxy S24 Ultra"
            search_query = f"{device.brand} {device.marketing_name}"
            
            print(f"[Login] Scraping price for: {search_query}")
            
            # Lakukan scraping ke Tokopedia
            scraped = tokopedia_scraper.search_price(search_query)
            
            if scraped:
                # Scraping berhasil!
                scraped_price_min = scraped.min_price
                scraped_price_max = scraped.max_price
                tokopedia_url = scraped.search_url
                price_source = 'tokopedia'
                
                print(f"[Login] Tokopedia price found: Rp {scraped_price_min:,} - Rp {scraped_price_max:,}")
            else:
                # Scraping gagal, gunakan harga dari database jika ada
                if device.price_idr > 0:
                    price_source = 'database'
                    print(f"[Login] Using database price: Rp {device.price_idr:,}")
                else:
                    print(f"[Login] No price available")
        
            # Generate URL Tokopedia untuk referensi (meskipun scraping gagal)
            if not tokopedia_url:
                tokopedia_url = tokopedia_scraper.get_search_url(search_query)
        
        # ----------------------------------------------------------------------
        # STEP 7: Simpan semua data ke database SQLite
        # ----------------------------------------------------------------------
        # Build extended user agent (tambahkan info Client Hints jika ada)
        extended_ua = user_agent
        if ch_model:
            extended_ua += f" [CH-Model: {ch_model}]"
        
        # Log ke database dengan semua informasi
        login_db.log_login(
            username=username,
            user_agent=extended_ua,
            model_code=parsed.model_code,
            brand=device.brand if device else None,
            marketing_name=device.marketing_name if device else parsed.model_code,
            price_idr=device.price_idr if device else 0,
            os_type=parsed.os_type,
            os_version=parsed.os_version,
            browser=parsed.browser,
            ip_address=ip_address,
            # Parameter baru untuk scraped price
            scraped_price_min=scraped_price_min,
            scraped_price_max=scraped_price_max,
            price_source=price_source,
            tokopedia_url=tokopedia_url
        )
        
        print(f"[Login] === Login Processed Successfully ===\n")
        
        # ----------------------------------------------------------------------
        # STEP 8: Return halaman sukses dengan info device
        # ----------------------------------------------------------------------
        return render_template('login_success.html',
            username=username,
            device=device,
            parsed=parsed,
            client_hints={
                'model': ch_model,
                'platform': ch_platform,
                'platform_version': ch_platform_version,
                'mobile': ch_mobile
            },
            # Data baru untuk display harga Tokopedia
            scraped_price_min=scraped_price_min,
            scraped_price_max=scraped_price_max,
            tokopedia_url=tokopedia_url
        )
    
    # ==========================================================================
    # GET REQUEST: Tampilkan form login
    # ==========================================================================
    # Buat response dengan template login
    response = make_response(render_template('login.html'))
    
    # Request Client Hints dari browser
    # Header ini meminta browser untuk mengirim info device yang lebih detail
    response.headers['Accept-CH'] = 'Sec-CH-UA-Model, Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Mobile, Sec-CH-UA-Full-Version-List'
    response.headers['Critical-CH'] = 'Sec-CH-UA-Model'
    response.headers['Permissions-Policy'] = 'ch-ua-model=(self), ch-ua-platform=(self)'
    
    return response


@main.route('/dashboard')
def dashboard():
    """Admin Dashboard with reports"""
    stats = login_db.get_stats()
    device_summary = login_db.get_device_summary()[:20]  # Top 20
    brand_summary = login_db.get_brand_summary()
    recent_logs = login_db.get_all_logs(limit=50)
    db_stats = device_db.stats()
    
    return render_template('dashboard.html',
        stats=stats,
        device_summary=device_summary,
        brand_summary=brand_summary,
        recent_logs=recent_logs,
        db_stats=db_stats
    )


@main.route('/api/devices')
def api_devices():
    """API: Get all logged devices"""
    logs = login_db.get_all_logs(limit=500)
    return jsonify({
        'success': True,
        'count': len(logs),
        'devices': logs
    })


@main.route('/api/report')
def api_report():
    """
    API: Report Summary
    
    Endpoint ini mengembalikan ringkasan statistik dalam format JSON.
    Berguna untuk integrasi dengan sistem lain atau dashboard custom.
    
    Returns:
        JSON dengan statistik, summary per device, dan summary per brand
    """
    stats = login_db.get_stats()
    device_summary = login_db.get_device_summary()
    brand_summary = login_db.get_brand_summary()
    
    return jsonify({
        'success': True,
        'stats': stats,
        'by_device': device_summary,
        'by_brand': brand_summary
    })


@main.route('/api/export/<format>')
def api_export(format):
    """
    API: Export Data
    
    Export data log ke file CSV atau JSON.
    File akan disimpan di folder 'output' dan path-nya dikembalikan.
    
    Args:
        format: 'csv' atau 'json'
        
    Returns:
        JSON dengan path ke file yang di-export
    """
    if format == 'csv':
        filepath = report_gen.export_csv()
        return jsonify({'success': True, 'file': filepath})
    elif format == 'json':
        filepath = report_gen.export_json()
        return jsonify({'success': True, 'file': filepath})
    else:
        return jsonify({'success': False, 'error': 'Invalid format'}), 400


@main.route('/api/test-ua')
def api_test_ua():
    """
    API: Test User-Agent Parser
    
    Endpoint untuk debugging - test bagaimana sistem parse User-Agent.
    Bisa diakses dengan parameter ?ua=<user_agent_string>
    
    Contoh:
        /api/test-ua?ua=Mozilla/5.0 (Linux; Android 14; SM-S911B)...
        
    Returns:
        JSON dengan hasil parsing dan device yang cocok
    """
    user_agent = request.args.get('ua', request.headers.get('User-Agent', ''))
    
    parsed = ua_parser.parse(user_agent)
    model_codes = ua_parser.extract_model_codes(user_agent)
    
    device = None
    for code in model_codes:
        device = device_db.find_device(code)
        if device:
            break
    
    if not device and parsed.model_code:
        device = device_db.search_device(parsed.model_code)
    
    return jsonify({
        'user_agent': user_agent,
        'parsed': {
            'model_code': parsed.model_code,
            'os_type': parsed.os_type,
            'os_version': parsed.os_version,
            'browser': parsed.browser
        },
        'extracted_codes': model_codes,
        'matched_device': {
            'brand': device.brand,
            'model_code': device.model_code,
            'marketing_name': device.marketing_name,
            'price_idr': device.price_idr
        } if device else None
    })


@main.route('/api/clear-logs', methods=['POST'])
def api_clear_logs():
    """
    API: Clear All Logs
    
    HATI-HATI! Endpoint ini menghapus SEMUA log login dari database.
    Gunakan dengan bijak, data yang dihapus tidak bisa dikembalikan.
    
    Method: POST (untuk keamanan)
    
    Returns:
        JSON dengan jumlah record yang dihapus
    """
    count = login_db.clear_logs()
    return jsonify({
        'success': True,
        'deleted': count
    })


# =============================================================================
# API ENDPOINT BARU - PRICE SCRAPING
# =============================================================================

@main.route('/api/scrape-price/<device_name>')
def api_scrape_price(device_name):
    """
    ========================================================================
    API: Manual Price Scraping dari Tokopedia
    ========================================================================
    
    Endpoint ini memungkinkan scraping harga secara manual untuk device tertentu.
    Berguna untuk testing atau mendapatkan harga tanpa harus login.
    
    CARA PAKAI:
    -----------
    GET /api/scrape-price/Samsung%20Galaxy%20S24
    
    URL harus di-encode. Contoh:
    - "Samsung Galaxy S24" -> "Samsung%20Galaxy%20S24"
    - "iPhone 15 Pro Max" -> "iPhone%2015%20Pro%20Max"
    
    Args:
        device_name: Nama device yang ingin dicari harganya
        
    Returns:
        JSON dengan informasi harga:
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
        
    Error Response (jika tidak ada harga):
        {
            "success": false,
            "error": "No price found for: Samsung Galaxy S24",
            "tokopedia_url": "https://tokopedia.com/search?q=..."
        }
    """
    print(f"\n[API] === Manual Price Scrape Request ===")
    print(f"[API] Device: {device_name}")
    
    # Lakukan scraping
    scraped = tokopedia_scraper.search_price(device_name)
    
    # Siapkan URL Tokopedia (selalu generate, meskipun scraping gagal)
    tokopedia_url = tokopedia_scraper.get_search_url(device_name)
    
    if scraped:
        # Scraping berhasil
        print(f"[API] Price found: Rp {scraped.min_price:,} - Rp {scraped.max_price:,}")
        return jsonify({
            'success': True,
            'device': device_name,
            'price': {
                'min': scraped.min_price,
                'max': scraped.max_price,
                'avg': scraped.avg_price,
                'product_count': scraped.product_count,
                'scraped_at': scraped.scraped_at.isoformat()
            },
            'tokopedia_url': tokopedia_url
        })
    else:
        # Scraping gagal
        print(f"[API] No price found")
        return jsonify({
            'success': False,
            'error': f'No price found for: {device_name}',
            'device': device_name,
            'tokopedia_url': tokopedia_url
        }), 404


@main.route('/api/scraper-cache/clear', methods=['POST'])
def api_clear_scraper_cache():
    """
    API: Clear Scraper Cache
    
    Menghapus semua cache hasil scraping.
    Berguna jika ingin mendapatkan data harga terbaru.
    
    Method: POST (untuk keamanan)
    
    Returns:
        JSON dengan jumlah cache item yang dihapus
    """
    count = tokopedia_scraper.clear_cache()
    return jsonify({
        'success': True,
        'cleared': count,
        'message': f'Cleared {count} cached price entries'
    })


"""
=============================================================================
💡 THE SMART PRICE SCRAPER - Tokopedia Edition
=============================================================================

Modul scraping harga PROFESIONAL untuk tugas intern.
Menggunakan metodologi "Crowd Wisdom" + Statistical Cleaning untuk
mendapatkan "Current Market Price" yang akurat dan wajar.

FITUR UTAMA:
============
1. Pre-Filter URL:
   - Condition: NEW (Baru/BNIB) - hindari barang second
   - Seller: Official Store & Power Merchant - toko terpercaya
   - Sort: Ulasan Terbanyak - bukti barang valid & laku

2. Sampling:
   - Ambil 10-20 harga dari produk teratas
   - Bukan hanya 1 harga, tapi sampel untuk statistik

3. Data Cleaning (Anti-Outlier):
   - Trim 15% termurah (buang Flash Sale/Promo gila)
   - Trim 15% termahal (buang toko lupa update/overprice)
   - Hasilnya: Middle 70% data = "Harga Normal"

4. Statistical Calculation:
   - Gunakan MEDIAN (nilai tengah), bukan AVERAGE
   - Median lebih tahan terhadap outlier ekstrem

KENAPA APPROACH INI?
====================
- Universal: HP baru rilis atau HP 3 tahun lalu, logic tetap jalan
- Anti-Promo: Harga Flash Sale otomatis terbuang sebagai outlier
- Realistis: Harga yang didapat = harga yang benar-benar dibayar orang
- Defensible: Bisa dijelaskan ke atasan dengan alasan statistik

Author: Intern WiFi Device Identifier Team
Created: December 2025
=============================================================================
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import statistics
import urllib.parse
import time


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MarketPrice:
    """
    Hasil scraping harga dengan metodologi "Smart Scraper"
    
    Attributes:
        market_price: Harga pasar wajar (MEDIAN dari data bersih)
        min_price: Harga terendah VALID (setelah cleaning)
        max_price: Harga tertinggi VALID (setelah cleaning)
        sample_count: Jumlah sampel yang dianalisis
        raw_count: Jumlah harga mentah sebelum cleaning
        confidence: Tingkat kepercayaan (high/medium/low)
        search_url: URL pencarian untuk referensi
        scraped_at: Waktu scraping
    """
    market_price: int          # Harga pasar wajar (MEDIAN)
    min_price: int             # Harga terendah valid
    max_price: int             # Harga tertinggi valid  
    sample_count: int          # Jumlah sampel valid
    raw_count: int             # Jumlah data mentah
    confidence: str            # Tingkat kepercayaan
    search_url: str            # URL Tokopedia
    scraped_at: datetime       # Waktu scraping


# =============================================================================
# MAIN SCRAPER CLASS
# =============================================================================

class TokopediaScraper:
    """
    ========================================================================
    🧠 THE SMART TOKOPEDIA SCRAPER
    ========================================================================
    
    Scraper profesional dengan metodologi statistik untuk mendapatkan
    "Current Market Price" yang akurat dan tahan banting.
    
    WORKFLOW:
    ---------
    1. Buat URL dengan filter (Official Store, New, Sort by Review)
    2. Fetch halaman dan extract 10-20 harga
    3. Clean data: Buang 15% termurah dan 15% termahal
    4. Hitung MEDIAN dari data bersih
    5. Return MarketPrice dengan confidence level
    
    PENGGUNAAN:
    -----------
    scraper = TokopediaScraper()
    result = scraper.get_market_price("Samsung Galaxy S24")
    
    if result:
        print(f"Harga Pasar: Rp {result.market_price:,}")
        print(f"Range Valid: Rp {result.min_price:,} - Rp {result.max_price:,}")
        print(f"Confidence: {result.confidence}")
    """
    
    # =========================================================================
    # KONFIGURASI
    # =========================================================================
    
    # Base URL Tokopedia Search dengan parameter filter
    TOKOPEDIA_BASE = "https://www.tokopedia.com/search"
    
    # Headers agar terlihat seperti browser Chrome biasa
    # PENTING: Jangan pakai default Python requests!
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # Konfigurasi sampling
    MIN_SAMPLES = 5           # Minimal sampel untuk hasil valid
    TARGET_SAMPLES = 15       # Target jumlah sampel
    
    # Konfigurasi cleaning (dalam persentase)
    TRIM_BOTTOM_PERCENT = 0.15    # Buang 15% termurah (Flash Sale/Promo)
    TRIM_TOP_PERCENT = 0.15       # Buang 15% termahal (Overprice)
    
    # Rate limiting dan caching
    CACHE_DURATION = 3600         # Cache 1 jam
    REQUEST_DELAY = 2.0           # 2 detik antar request (aman dari ban)
    
    # Range harga valid untuk smartphone (filter noise)
    PRICE_MIN = 500_000           # 500rb (HP paling murah)
    PRICE_MAX = 50_000_000        # 50jt (Flagship paling mahal)
    
    def __init__(self):
        """
        Inisialisasi Smart Scraper
        
        - Session untuk connection pooling
        - Cache untuk efisiensi
        - Rate limiter untuk keamanan
        """
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)
        
        # Cache: key = query, value = (MarketPrice, timestamp)
        self._cache: Dict[str, Tuple[MarketPrice, datetime]] = {}
        
        # Rate limiting
        self._last_request: Optional[datetime] = None
        
        print("[SmartScraper] 🧠 Tokopedia Smart Scraper initialized")
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def get_market_price(self, device_name: str) -> Optional[MarketPrice]:
        """
        ====================================================================
        🎯 MAIN METHOD: Dapatkan Harga Pasar Wajar
        ====================================================================
        
        Ini adalah method utama yang dipanggil dari aplikasi.
        Menggabungkan semua tahapan: search, extract, clean, calculate.
        
        ALUR KERJA:
        1. Normalize query (hapus karakter aneh)
        2. Cek cache (kalau ada dan masih valid, return langsung)
        3. Buat URL dengan filter Smart
        4. Fetch dan extract harga
        5. Cleaning: Buang outlier atas dan bawah
        6. Hitung MEDIAN sebagai Market Price
        7. Tentukan confidence level
        8. Simpan ke cache dan return
        
        Args:
            device_name: Nama device lengkap
                        Contoh: "Samsung Galaxy S24 Ultra 256GB"
                        
        Returns:
            MarketPrice object dengan harga pasar, atau None jika gagal
            
        Example:
            >>> scraper = TokopediaScraper()
            >>> price = scraper.get_market_price("iPhone 15 Pro Max")
            >>> if price:
            ...     print(f"Harga Pasar: Rp {price.market_price:,}")
            ...     print(f"Range: Rp {price.min_price:,} - Rp {price.max_price:,}")
            ...     print(f"Confidence: {price.confidence}")
        """
        if not device_name or len(device_name.strip()) < 3:
            print(f"[SmartScraper] ⚠️ Query terlalu pendek: '{device_name}'")
            return None
        
        # Normalize query
        query = self._normalize_query(device_name)
        print(f"\n[SmartScraper] 🔍 Mencari harga pasar untuk: '{query}'")
        
        # STEP 1: Cek cache
        cached = self._get_from_cache(query)
        if cached:
            print(f"[SmartScraper] ✅ Cache hit! Market price: Rp {cached.market_price:,}")
            return cached
        
        # STEP 2: Rate limiting (hindari ban IP)
        self._apply_rate_limit()
        
        # STEP 3: Buat URL dengan Smart Filter
        search_url = self._build_smart_url(query)
        print(f"[SmartScraper] 📡 Fetching: {search_url[:80]}...")
        
        # STEP 4: Fetch dan extract harga mentah
        raw_prices = self._fetch_prices(search_url)
        
        if not raw_prices:
            print(f"[SmartScraper] ❌ Gagal mendapatkan harga")
            return None
        
        print(f"[SmartScraper] 📊 Raw data: {len(raw_prices)} harga ditemukan")
        
        # STEP 5: Data Cleaning (Buang Outlier)
        clean_prices = self._clean_prices(raw_prices)
        
        if len(clean_prices) < self.MIN_SAMPLES:
            print(f"[SmartScraper] ⚠️ Data terlalu sedikit setelah cleaning: {len(clean_prices)}")
            # Fallback: gunakan semua data tanpa cleaning
            clean_prices = raw_prices
        
        # STEP 6: Hitung Market Price (MEDIAN!)
        market_price = self._calculate_market_price(clean_prices)
        
        # STEP 7: Tentukan Confidence Level
        confidence = self._determine_confidence(len(raw_prices), len(clean_prices))
        
        # STEP 8: Buat result object
        result = MarketPrice(
            market_price=market_price,
            min_price=min(clean_prices),
            max_price=max(clean_prices),
            sample_count=len(clean_prices),
            raw_count=len(raw_prices),
            confidence=confidence,
            search_url=search_url,
            scraped_at=datetime.now()
        )
        
        # Simpan ke cache
        self._save_to_cache(query, result)
        
        print(f"[SmartScraper] ✅ Market Price: Rp {result.market_price:,}")
        print(f"[SmartScraper] 📈 Range Valid: Rp {result.min_price:,} - Rp {result.max_price:,}")
        print(f"[SmartScraper] 🎯 Confidence: {result.confidence} ({result.sample_count}/{result.raw_count} samples)")
        
        return result
    
    def get_search_url(self, device_name: str) -> str:
        """
        Generate URL pencarian Tokopedia dengan Smart Filter
        
        URL ini bisa diberikan ke user agar mereka bisa cek sendiri
        di Tokopedia apakah harga yang kita sajikan masuk akal.
        """
        query = self._normalize_query(device_name)
        return self._build_smart_url(query)
    
    def clear_cache(self) -> int:
        """
        Hapus semua cache scraping
        
        Returns:
            Jumlah entry yang dihapus
        """
        count = len(self._cache)
        self._cache.clear()
        print(f"[SmartScraper] 🗑️ Cache cleared: {count} entries")
        return count
    
    # =========================================================================
    # PRIVATE METHODS - URL Building
    # =========================================================================
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize search query
        
        Langkah:
        1. Hapus karakter khusus (kecuali space & alfanumerik)
        2. Lowercase
        3. Hapus double space
        
        Contoh:
            "Samsung Galaxy S24+" -> "samsung galaxy s24"
            "iPhone 15 Pro Max (256GB)" -> "iphone 15 pro max 256gb"
        """
        # Hapus karakter khusus kecuali space dan alfanumerik
        cleaned = re.sub(r'[^\w\s]', '', query)
        # Lowercase dan bersihkan space
        normalized = ' '.join(cleaned.lower().split())
        return normalized
    
    def _build_smart_url(self, query: str) -> str:
        """
        Build URL Tokopedia dengan SMART FILTER
        
        ==== FILTER YANG DITERAPKAN ====
        
        1. condition=1 -> Barang BARU saja (bukan second)
        
        2. rt=4,5 -> Rating 4-5 bintang (toko bagus)
        
        3. goldmerchant=true -> Official Store & Power Merchant
           Ini penting untuk filter toko abal-abal!
        
        4. ob=5 -> Sort by: Ulasan Terbanyak
           Kenapa bukan "Harga Terendah"?
           - Harga terendah = banyak sampah/penipuan
           - Ulasan terbanyak = barang valid, laku, harga wajar
        
        5. rows=30 -> Ambil 30 produk per halaman
        """
        # Encode query untuk URL
        encoded_query = urllib.parse.quote(query)
        
        # Build URL dengan filter
        params = {
            'q': query,               # Keyword pencarian
            'condition': '1',         # 1 = New/Baru only
            'rt': '4,5',             # Rating 4-5 bintang
            'goldmerchant': 'true',   # Official Store & Power Merchant
            'ob': '5',                # Sort: Ulasan Terbanyak
            'rows': '30',             # 30 produk per halaman
        }
        
        # Buat URL
        query_string = urllib.parse.urlencode(params)
        url = f"{self.TOKOPEDIA_BASE}?{query_string}"
        
        return url
    
    # =========================================================================
    # PRIVATE METHODS - Fetching & Extracting
    # =========================================================================
    
    def _fetch_prices(self, url: str) -> List[int]:
        """
        Fetch halaman Tokopedia dan extract semua harga
        
        STRATEGI EXTRACTION:
        - Cari semua pattern harga "RpX.XXX.XXX"
        - Parse dengan Regex yang robust
        - Filter hanya harga dalam range smartphone
        
        Returns:
            List of prices (integer) dalam Rupiah
        """
        try:
            response = self._session.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"[SmartScraper] ⚠️ HTTP {response.status_code}")
                return []
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract harga
            prices = self._extract_prices_from_html(soup)
            
            return prices
            
        except requests.Timeout:
            print(f"[SmartScraper] ⏱️ Request timeout")
            return []
        except requests.RequestException as e:
            print(f"[SmartScraper] ❌ Request error: {str(e)}")
            return []
    
    def _extract_prices_from_html(self, soup: BeautifulSoup) -> List[int]:
        """
        Extract dan parse harga dari HTML Tokopedia
        
        REGEX PATTERN untuk harga Indonesia:
        - "Rp1.234.567" atau "Rp 1.234.567"
        - "Rp1234567" (tanpa titik)
        - "Rp1,234,567" (dengan koma)
        
        LANGKAH:
        1. Cari semua text dengan pattern Rp
        2. Extract angka dengan regex
        3. Convert ke integer
        4. Filter hanya range harga smartphone
        """
        prices = []
        
        # Regex pattern untuk mencocokkan harga Indonesia
        # Pattern ini akan match:
        # - Rp1.234.567
        # - Rp 1.234.567
        # - Rp1,234,567
        # - Rp1234567
        price_pattern = re.compile(r'Rp\s*[\d\.\,]+')
        
        # Ambil semua text dari halaman
        all_text = soup.get_text()
        
        # Cari semua match
        matches = price_pattern.findall(all_text)
        
        for price_str in matches:
            price_int = self._parse_price_string(price_str)
            
            if price_int and self.PRICE_MIN <= price_int <= self.PRICE_MAX:
                prices.append(price_int)
        
        # Hapus duplikat sambil menjaga urutan
        seen = set()
        unique_prices = []
        for p in prices:
            if p not in seen:
                seen.add(p)
                unique_prices.append(p)
        
        return unique_prices
    
    def _parse_price_string(self, price_str: str) -> Optional[int]:
        """
        Parse string harga Indonesia ke integer
        
        INPUT:
            "Rp1.234.567" atau "Rp 1.234.567" atau "Rp1234567"
            
        OUTPUT:
            1234567 (integer)
            
        REGEX EXPLANATION:
        1. Hapus "Rp" dan spasi
        2. Hapus titik (.) yang merupakan separator ribuan
        3. Hapus koma (,) kalau ada
        4. Convert ke int
        
        KENAPA KOMPLEKS?
        - Format Indonesia: "Rp1.234.567" (titik sebagai separator ribuan)
        - Kadang ada yang pakai: "Rp1,234,567" (koma)
        - Kadang tanpa separator: "Rp1234567"
        """
        try:
            # Hapus "Rp", spasi, titik, dan koma
            clean = price_str.replace('Rp', '')
            clean = clean.replace(' ', '')
            clean = clean.replace('.', '')
            clean = clean.replace(',', '')
            
            # Convert ke int
            return int(clean)
            
        except (ValueError, AttributeError):
            return None
    
    # =========================================================================
    # PRIVATE METHODS - Statistical Cleaning
    # =========================================================================
    
    def _clean_prices(self, prices: List[int]) -> List[int]:
        """
        ====================================================================
        🧹 DATA CLEANING - Kunci Keberhasilan Smart Scraper!
        ====================================================================
        
        METHOD: Trimmed Data / Winsorization
        
        LANGKAH:
        1. Sort harga dari terendah ke tertinggi
        2. Buang 15% data TERMURAH (Flash Sale, Promo, Penipuan)
        3. Buang 15% data TERMAHAL (Toko lupa update, Overprice)
        4. Sisakan 70% data DI TENGAH = "Harga Normal"
        
        KENAPA INI PENTING?
        - Flash Sale: 1 toko promo gila-gilaan → BUANG
        - Penipuan: Harga aneh di bawah pasar → BUANG
        - Overprice: Toko sudut yang harga tinggi → BUANG
        
        CONTOH:
        Raw: [4.5jt, 8.4jt, 8.5jt, 8.5jt, 8.6jt, 8.6jt, 8.7jt, 11jt]
        
        Buang bawah (15%): [4.5jt] → hilang (Flash Sale)
        Buang atas (15%): [11jt] → hilang (Overprice)
        
        Clean: [8.4jt, 8.5jt, 8.5jt, 8.6jt, 8.6jt, 8.7jt]
        
        Median dari clean = 8.55jt ← HARGA PASAR WAJAR!
        """
        if len(prices) < 3:
            # Data terlalu sedikit, tidak perlu cleaning
            return prices
        
        # Sort dari terendah ke tertinggi
        sorted_prices = sorted(prices)
        
        # Hitung berapa data yang akan dibuang
        total = len(sorted_prices)
        cut_bottom = int(total * self.TRIM_BOTTOM_PERCENT)
        cut_top = int(total * self.TRIM_TOP_PERCENT)
        
        # Minimal buang 1 jika ada cukup data
        if total >= 6:
            cut_bottom = max(1, cut_bottom)
            cut_top = max(1, cut_top)
        
        # Slicing: buang bawah dan atas
        if cut_top == 0:
            clean_prices = sorted_prices[cut_bottom:]
        else:
            clean_prices = sorted_prices[cut_bottom : -cut_top]
        
        print(f"[SmartScraper] 🧹 Cleaning: {total} → {len(clean_prices)} samples")
        print(f"[SmartScraper]    Removed: {cut_bottom} lowest, {cut_top} highest")
        
        return clean_prices
    
    def _calculate_market_price(self, prices: List[int]) -> int:
        """
        Hitung MARKET PRICE menggunakan MEDIAN
        
        KENAPA MEDIAN, BUKAN MEAN (RATA-RATA)?
        ==========================================
        
        Mean (Rata-rata):
            Contoh: [1jt, 8jt, 8jt, 8jt, 20jt]
            Mean = (1+8+8+8+20)/5 = 9jt ← Terdistorsi!
        
        Median (Nilai Tengah):
            Contoh: [1jt, 8jt, 8jt, 8jt, 20jt]
            Median = 8jt ← Stabil!
        
        Median tidak terpengaruh oleh nilai ekstrem di ujung.
        Kalau ada 1 toko promo atau 1 toko mahal, median tetap OK.
        
        ALASAN BUAT LAPORAN KE ATASAN:
        "Saya menggunakan Median karena lebih robust terhadap outlier.
        Kalau ada flash sale atau toko overprice, hasilnya tetap akurat
        karena Median mengambil nilai tengah, bukan rata-rata yang bisa
        terdistorsi oleh nilai ekstrem."
        """
        if not prices:
            return 0
        
        # Gunakan statistics.median (built-in Python)
        median_price = statistics.median(prices)
        
        # Round ke ribuan terdekat untuk angka lebih rapi
        rounded = round(median_price / 1000) * 1000
        
        return rounded
    
    def _determine_confidence(self, raw_count: int, clean_count: int) -> str:
        """
        Tentukan tingkat kepercayaan hasil
        
        CONFIDENCE LEVELS:
        - high: >= 10 sampel bersih (sangat reliable)
        - medium: 5-9 sampel bersih (cukup reliable)
        - low: < 5 sampel bersih (mungkin tidak akurat)
        
        BISA DIJELASKAN KE ATASAN:
        "Confidence 'high' berarti kami punya >= 10 data point dari
        toko terpercaya. 'Medium' berarti 5-9 data point. 'Low' berarti
        data kurang dari 5, jadi hasilnya mungkin kurang representatif."
        """
        if clean_count >= 10:
            return "high"
        elif clean_count >= 5:
            return "medium"
        else:
            return "low"
    
    # =========================================================================
    # PRIVATE METHODS - Caching & Rate Limiting
    # =========================================================================
    
    def _get_from_cache(self, query: str) -> Optional[MarketPrice]:
        """Get hasil dari cache jika masih valid"""
        if query not in self._cache:
            return None
        
        cached_result, cached_time = self._cache[query]
        
        # Cek apakah belum expired
        if datetime.now() - cached_time < timedelta(seconds=self.CACHE_DURATION):
            return cached_result
        
        # Expired, hapus
        del self._cache[query]
        return None
    
    def _save_to_cache(self, query: str, result: MarketPrice) -> None:
        """Simpan hasil ke cache"""
        self._cache[query] = (result, datetime.now())
    
    def _apply_rate_limit(self) -> None:
        """
        Rate Limiting - SANGAT PENTING!
        
        Jangan nembak request terlalu cepat ke Tokopedia.
        Kalau kena ban IP kantor/kampus gara-gara kamu, bahaya! 😅
        
        Default: 2 detik antar request
        """
        if self._last_request:
            elapsed = (datetime.now() - self._last_request).total_seconds()
            if elapsed < self.REQUEST_DELAY:
                sleep_time = self.REQUEST_DELAY - elapsed
                print(f"[SmartScraper] 💤 Rate limit: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        self._last_request = datetime.now()


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================
# Untuk kompatibilitas dengan kode lama yang pakai ScrapedPrice

@dataclass
class ScrapedPrice:
    """Legacy class - untuk backward compatibility"""
    min_price: int
    max_price: int
    avg_price: int
    product_count: int
    search_url: str
    scraped_at: datetime


# Method wrapper untuk backward compatibility
def _legacy_search_price(self, device_name: str) -> Optional[ScrapedPrice]:
    """Wrapper untuk kompatibilitas dengan kode lama"""
    result = self.get_market_price(device_name)
    
    if not result:
        return None
    
    return ScrapedPrice(
        min_price=result.min_price,
        max_price=result.max_price,
        avg_price=result.market_price,  # Market price sebagai "avg"
        product_count=result.sample_count,
        search_url=result.search_url,
        scraped_at=result.scraped_at
    )

# Tambahkan method ke class
TokopediaScraper.search_price = _legacy_search_price


# =============================================================================
# TESTING / DEBUG
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧠 TESTING: THE SMART TOKOPEDIA SCRAPER")
    print("="*70 + "\n")
    
    # Buat instance scraper
    scraper = TokopediaScraper()
    
    # Test dengan beberapa device
    test_devices = [
        "Samsung Galaxy S24 Ultra",
        "iPhone 15 Pro Max 256GB",
        "Xiaomi Redmi Note 13 Pro",
    ]
    
    for device in test_devices:
        print(f"\n{'─'*60}")
        print(f"📱 Testing: {device}")
        print('─'*60)
        
        result = scraper.get_market_price(device)
        
        if result:
            print(f"\n📊 RESULT:")
            print(f"   Market Price : Rp {result.market_price:,.0f}")
            print(f"   Price Range  : Rp {result.min_price:,.0f} - Rp {result.max_price:,.0f}")
            print(f"   Samples      : {result.sample_count} valid / {result.raw_count} raw")
            print(f"   Confidence   : {result.confidence}")
            print(f"   URL          : {result.search_url[:60]}...")
        else:
            print("\n   ❌ FAILED - No price data available")
        
        # Delay antar test
        if device != test_devices[-1]:
            print("\n   ⏳ Waiting 3s before next test...")
            time.sleep(3)
    
    print("\n" + "="*70)
    print("✅ Testing complete!")
    print("="*70)

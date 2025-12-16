"""
=============================================================================
TOKOPEDIA PRICE SCRAPER MODULE
=============================================================================

Modul ini bertugas untuk melakukan scraping harga perangkat dari Tokopedia.
Ketika user login ke captive portal WiFi, sistem akan mengidentifikasi 
device mereka dan mencari perkiraan harga device tersebut di Tokopedia.

CARA KERJA:
1. Menerima nama device (contoh: "Samsung Galaxy S24 Ultra")
2. Melakukan request ke Tokopedia search API/page
3. Extract harga dari hasil pencarian
4. Return range harga (min-max) dari berbagai penjual

CATATAN PENTING:
- Menggunakan caching untuk mengurangi request ke Tokopedia
- Headers di-set agar request terlihat seperti browser normal
- Rate limiting diterapkan untuk menghindari IP blocking
- Jika scraping gagal, akan return None (fallback ke harga database)

Author: WiFi Device Identifier Team
Created: December 2025
=============================================================================
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import json
import urllib.parse
import time


@dataclass
class ScrapedPrice:
    """
    Data class untuk menyimpan hasil scraping harga
    
    Attributes:
        min_price: Harga terendah yang ditemukan (dalam Rupiah)
        max_price: Harga tertinggi yang ditemukan (dalam Rupiah)
        avg_price: Harga rata-rata dari semua hasil
        product_count: Jumlah produk yang ditemukan
        search_url: URL pencarian Tokopedia (untuk referensi user)
        scraped_at: Waktu scraping dilakukan
    """
    min_price: int
    max_price: int
    avg_price: int
    product_count: int
    search_url: str
    scraped_at: datetime


class TokopediaScraper:
    """
    ==========================================================================
    TOKOPEDIA PRICE SCRAPER
    ==========================================================================
    
    Class untuk melakukan scraping harga dari Tokopedia.
    
    PENGGUNAAN:
    -----------
    scraper = TokopediaScraper()
    result = scraper.search_price("iPhone 15 Pro Max")
    
    if result:
        print(f"Harga: Rp {result.min_price:,} - Rp {result.max_price:,}")
    
    FITUR:
    ------
    - Caching hasil scraping (default 1 jam)
    - Custom headers untuk menghindari blocking
    - Error handling yang robust
    - Rate limiting otomatis
    """
    
    # -------------------------------------------------------------------------
    # KONSTANTA KONFIGURASI
    # -------------------------------------------------------------------------
    
    # Base URL untuk pencarian Tokopedia
    TOKOPEDIA_SEARCH_URL = "https://www.tokopedia.com/search"
    
    # Headers untuk request - dibuat mirip browser normal
    # Ini penting agar request tidak diblokir oleh Tokopedia
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    # Durasi cache dalam detik (1 jam = 3600 detik)
    CACHE_DURATION = 3600
    
    # Delay antar request dalam detik (untuk rate limiting)
    REQUEST_DELAY = 1.0
    
    def __init__(self):
        """
        Inisialisasi scraper
        
        Membuat:
        - Session requests untuk connection pooling
        - Cache dictionary untuk menyimpan hasil scraping
        - Timestamp tracking untuk rate limiting
        """
        # Session untuk reuse connection (lebih efisien)
        self._session = requests.Session()
        self._session.headers.update(self.DEFAULT_HEADERS)
        
        # Cache: key = query, value = (ScrapedPrice, timestamp)
        self._cache: Dict[str, Tuple[ScrapedPrice, datetime]] = {}
        
        # Tracking waktu request terakhir untuk rate limiting
        self._last_request_time: Optional[datetime] = None
        
        print("[Scraper] TokopediaScraper initialized")
    
    # -------------------------------------------------------------------------
    # PUBLIC METHODS - Method yang dipanggil dari luar
    # -------------------------------------------------------------------------
    
    def search_price(self, device_name: str) -> Optional[ScrapedPrice]:
        """
        MAIN METHOD: Mencari harga device di Tokopedia
        
        ALUR KERJA:
        1. Cek apakah hasil ada di cache dan masih valid
        2. Jika tidak, lakukan scraping ke Tokopedia
        3. Parse hasil dan extract harga
        4. Simpan ke cache
        5. Return hasil
        
        Args:
            device_name: Nama device yang dicari (contoh: "Samsung Galaxy S24")
                        
        Returns:
            ScrapedPrice object jika berhasil, None jika gagal
            
        Example:
            >>> scraper = TokopediaScraper()
            >>> price = scraper.search_price("iPhone 15 Pro")
            >>> if price:
            ...     print(f"Range: Rp {price.min_price:,} - Rp {price.max_price:,}")
        """
        if not device_name or len(device_name.strip()) < 3:
            print(f"[Scraper] Device name terlalu pendek: '{device_name}'")
            return None
        
        # Normalize query (hapus karakter khusus, lowercase)
        query = self._normalize_query(device_name)
        print(f"[Scraper] Mencari harga untuk: '{query}'")
        
        # STEP 1: Cek cache
        cached = self._get_from_cache(query)
        if cached:
            print(f"[Scraper] Cache hit! Menggunakan data cached")
            return cached
        
        # STEP 2: Rate limiting - tunggu jika request terlalu cepat
        self._apply_rate_limit()
        
        # STEP 3: Lakukan scraping
        try:
            result = self._scrape_tokopedia(query)
            
            if result:
                # STEP 4: Simpan ke cache
                self._save_to_cache(query, result)
                print(f"[Scraper] Berhasil! Harga: Rp {result.min_price:,} - Rp {result.max_price:,}")
                return result
            else:
                print(f"[Scraper] Tidak ada hasil untuk '{query}'")
                return None
                
        except Exception as e:
            print(f"[Scraper] Error saat scraping: {str(e)}")
            return None
    
    def get_search_url(self, device_name: str) -> str:
        """
        Generate URL pencarian Tokopedia untuk device tertentu
        
        Berguna untuk memberikan link langsung ke user agar mereka
        bisa melihat hasil pencarian sendiri di Tokopedia.
        
        Args:
            device_name: Nama device
            
        Returns:
            URL pencarian Tokopedia yang bisa diklik
        """
        query = self._normalize_query(device_name)
        encoded_query = urllib.parse.quote(query)
        return f"{self.TOKOPEDIA_SEARCH_URL}?q={encoded_query}"
    
    def clear_cache(self) -> int:
        """
        Hapus semua cache
        
        Returns:
            Jumlah item yang dihapus
        """
        count = len(self._cache)
        self._cache.clear()
        print(f"[Scraper] Cache cleared: {count} items removed")
        return count
    
    # -------------------------------------------------------------------------
    # PRIVATE METHODS - Method internal (tidak dipanggil dari luar)
    # -------------------------------------------------------------------------
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query pencarian
        
        Langkah-langkah:
        1. Hapus karakter khusus (kecuali spasi dan alfanumerik)
        2. Convert ke lowercase
        3. Hapus spasi berlebih
        
        Contoh:
            "Samsung Galaxy S24+" -> "samsung galaxy s24"
            "iPhone 15 Pro Max 256GB" -> "iphone 15 pro max 256gb"
        """
        # Hapus karakter khusus kecuali spasi dan alfanumerik
        cleaned = re.sub(r'[^\w\s]', '', query)
        # Lowercase dan hapus spasi berlebih
        normalized = ' '.join(cleaned.lower().split())
        return normalized
    
    def _get_from_cache(self, query: str) -> Optional[ScrapedPrice]:
        """
        Ambil hasil dari cache jika masih valid
        
        Cache dianggap valid jika umurnya kurang dari CACHE_DURATION
        
        Returns:
            ScrapedPrice jika ada di cache dan valid, None jika tidak
        """
        if query not in self._cache:
            return None
        
        cached_result, cached_time = self._cache[query]
        
        # Cek apakah cache masih valid (belum expired)
        if datetime.now() - cached_time < timedelta(seconds=self.CACHE_DURATION):
            return cached_result
        
        # Cache expired, hapus
        del self._cache[query]
        return None
    
    def _save_to_cache(self, query: str, result: ScrapedPrice) -> None:
        """
        Simpan hasil ke cache
        
        Args:
            query: Query pencarian (sebagai key)
            result: Hasil scraping (sebagai value)
        """
        self._cache[query] = (result, datetime.now())
    
    def _apply_rate_limit(self) -> None:
        """
        Terapkan rate limiting
        
        Jika request sebelumnya terlalu dekat, tunggu sebentar
        agar tidak membebani server Tokopedia
        """
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.REQUEST_DELAY:
                sleep_time = self.REQUEST_DELAY - elapsed
                print(f"[Scraper] Rate limiting: waiting {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self._last_request_time = datetime.now()
    
    def _scrape_tokopedia(self, query: str) -> Optional[ScrapedPrice]:
        """
        CORE METHOD: Melakukan scraping ke Tokopedia
        
        STRATEGI:
        Karena Tokopedia menggunakan JavaScript untuk rendering,
        kita mencoba beberapa pendekatan:
        
        1. Request ke halaman search biasa
        2. Parse HTML untuk mencari data harga
        3. Jika ada embedded JSON, extract dari situ
        
        Args:
            query: Query pencarian yang sudah dinormalize
            
        Returns:
            ScrapedPrice jika berhasil extract harga, None jika gagal
        """
        # Build URL pencarian
        search_url = self.get_search_url(query)
        
        try:
            # Lakukan HTTP GET request
            print(f"[Scraper] Fetching: {search_url}")
            response = self._session.get(search_url, timeout=10)
            
            # Cek status code
            if response.status_code != 200:
                print(f"[Scraper] HTTP Error: {response.status_code}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Coba extract harga dari berbagai sumber
            prices = self._extract_prices_from_html(soup)
            
            if not prices:
                print(f"[Scraper] Tidak menemukan harga di HTML")
                return None
            
            # Hitung statistik
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) // len(prices)
            
            return ScrapedPrice(
                min_price=min_price,
                max_price=max_price,
                avg_price=avg_price,
                product_count=len(prices),
                search_url=search_url,
                scraped_at=datetime.now()
            )
            
        except requests.Timeout:
            print(f"[Scraper] Request timeout")
            return None
        except requests.RequestException as e:
            print(f"[Scraper] Request error: {str(e)}")
            return None
    
    def _extract_prices_from_html(self, soup: BeautifulSoup) -> list:
        """
        Extract semua harga dari HTML Tokopedia
        
        Tokopedia biasanya menampilkan harga dalam format:
        - "Rp1.234.567" atau "Rp 1.234.567"
        - Dalam elemen dengan class tertentu
        
        Strategy:
        1. Cari semua elemen yang mengandung "Rp"
        2. Extract angka dari text tersebut
        3. Filter harga yang masuk akal (untuk HP: 500rb - 100jt)
        
        Returns:
            List of prices (integer) dalam Rupiah
        """
        prices = []
        
        # Pattern untuk mencocokkan harga dalam format Indonesia
        # Contoh: "Rp1.234.567" atau "Rp 1.234.567" atau "Rp1234567"
        price_pattern = re.compile(r'Rp\s*[\d\.]+')
        
        # Cari semua text yang mengandung pattern harga
        all_text = soup.get_text()
        price_matches = price_pattern.findall(all_text)
        
        for price_str in price_matches:
            try:
                # Hapus "Rp" dan titik, convert ke integer
                # "Rp1.234.567" -> 1234567
                clean_price = price_str.replace('Rp', '').replace('.', '').replace(' ', '').strip()
                price = int(clean_price)
                
                # Filter harga yang masuk akal untuk smartphone
                # Range: 500.000 (HP murah) sampai 100.000.000 (flagship premium)
                if 500_000 <= price <= 100_000_000:
                    prices.append(price)
                    
            except (ValueError, AttributeError):
                # Skip jika tidak bisa di-convert ke integer
                continue
        
        # Hapus duplikat dan sort
        prices = sorted(list(set(prices)))
        
        print(f"[Scraper] Found {len(prices)} valid prices")
        return prices


# =============================================================================
# TESTING / DEBUG
# =============================================================================
# Jika file ini dijalankan langsung (bukan di-import), jalankan test

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING TOKOPEDIA SCRAPER")
    print("="*60 + "\n")
    
    # Buat instance scraper
    scraper = TokopediaScraper()
    
    # Test dengan beberapa device
    test_devices = [
        "Samsung Galaxy S24 Ultra",
        "iPhone 15 Pro Max",
        "Xiaomi Redmi Note 13",
    ]
    
    for device in test_devices:
        print(f"\n--- Testing: {device} ---")
        result = scraper.search_price(device)
        
        if result:
            print(f"  Min Price: Rp {result.min_price:,.0f}")
            print(f"  Max Price: Rp {result.max_price:,.0f}")
            print(f"  Avg Price: Rp {result.avg_price:,.0f}")
            print(f"  Products Found: {result.product_count}")
            print(f"  URL: {result.search_url}")
        else:
            print("  [FAILED] Tidak dapat mengambil harga")

"""
=============================================================================
DATABASE MODELS - SQLite Models for WiFi Device Identifier
=============================================================================

Modul ini mengelola database SQLite untuk menyimpan log login pengguna.
Setiap kali seseorang login ke captive portal WiFi, informasi device
mereka akan dicatat di database ini.

TABEL YANG DIKELOLA:
- login_logs: Menyimpan semua log login dengan informasi device

FITUR BARU (Price Scraping):
- scraped_price_min: Harga minimum dari Tokopedia
- scraped_price_max: Harga maksimum dari Tokopedia
- price_source: Asal harga ('database', 'tokopedia', 'none')
- tokopedia_url: URL pencarian Tokopedia untuk referensi

Author: WiFi Device Identifier Team
=============================================================================
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager


class LoginDatabase:
    """
    ==========================================================================
    LOGIN DATABASE
    ==========================================================================
    
    Class untuk mengelola database SQLite yang menyimpan log login.
    
    PENGGUNAAN:
    -----------
    db = LoginDatabase("path/to/database.db")
    
    # Log login baru
    db.log_login(
        username="user1",
        user_agent="Mozilla/5.0...",
        model_code="SM-S911B",
        brand="Samsung",
        marketing_name="Galaxy S24",
        price_idr=15000000,
        ...
    )
    
    # Ambil statistik
    stats = db.get_stats()
    print(f"Total login: {stats['total_logins']}")
    """
    
    def __init__(self, db_path: str):
        """
        Inisialisasi database
        
        Args:
            db_path: Path ke file database SQLite
                    Contoh: "database/wifi_devices.db"
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """
        Inisialisasi tabel database
        
        Method ini akan:
        1. Membuat directory jika belum ada
        2. Membuat tabel login_logs jika belum ada
        3. Menambahkan kolom baru untuk fitur price scraping (migration)
        4. Membuat index untuk query yang sering digunakan
        """
        # Pastikan directory untuk database ada
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # ================================================================
            # TABEL UTAMA: login_logs
            # ================================================================
            # Tabel ini menyimpan semua log login dari captive portal
            # Setiap row = 1 kali login dari 1 user
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Informasi User --
                    username TEXT NOT NULL,          -- Username yang diinput saat login
                    ip_address TEXT,                 -- IP address user
                    
                    -- Informasi Device (dari User-Agent) --
                    user_agent TEXT,                 -- Raw User-Agent string
                    model_code TEXT,                 -- Kode model (contoh: SM-S911B)
                    brand TEXT,                      -- Merek (contoh: Samsung)
                    marketing_name TEXT,             -- Nama marketing (contoh: Galaxy S24)
                    
                    -- Informasi OS & Browser --
                    os_type TEXT,                    -- Tipe OS (android/ios/windows/etc)
                    os_version TEXT,                 -- Versi OS (contoh: 14.0)
                    browser TEXT,                    -- Browser yang digunakan
                    
                    -- Informasi Harga (dari database lokal) --
                    price_idr INTEGER DEFAULT 0,     -- Harga dari database CSV
                    
                    -- Informasi Harga (dari Tokopedia - FITUR BARU) --
                    scraped_price_min INTEGER,       -- Harga minimum dari scraping
                    scraped_price_max INTEGER,       -- Harga maksimum dari scraping
                    price_source TEXT DEFAULT 'none', -- Sumber harga: database/tokopedia/none
                    tokopedia_url TEXT,              -- URL pencarian Tokopedia
                    
                    -- Timestamp --
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Waktu login
                )
            ''')
            
            # ================================================================
            # MIGRATION: Tambah kolom baru untuk existing database
            # ================================================================
            # Jika database sudah ada sebelumnya, tambahkan kolom baru
            # SQLite tidak support ADD COLUMN IF NOT EXISTS, jadi kita cek manual
            self._migrate_add_columns(cursor)
            
            # ================================================================
            # INDEXES: Untuk mempercepat query
            # ================================================================
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_login_time ON login_logs(login_time)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_brand ON login_logs(brand)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_source ON login_logs(price_source)
            ''')
            
            conn.commit()
            print("[Database] Initialized successfully")
    
    def _migrate_add_columns(self, cursor) -> None:
        """
        Migration: Tambah kolom baru ke tabel existing
        
        Method ini menambahkan kolom-kolom baru yang diperlukan
        untuk fitur price scraping jika belum ada.
        
        CATATAN: SQLite tidak support ADD COLUMN IF NOT EXISTS,
        jadi kita harus cek dulu kolom yang ada.
        """
        # Ambil daftar kolom yang sudah ada
        cursor.execute("PRAGMA table_info(login_logs)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Kolom-kolom baru yang perlu ditambahkan
        new_columns = [
            ("scraped_price_min", "INTEGER"),
            ("scraped_price_max", "INTEGER"),
            ("price_source", "TEXT DEFAULT 'none'"),
            ("tokopedia_url", "TEXT"),
        ]
        
        # Tambahkan kolom yang belum ada
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE login_logs ADD COLUMN {col_name} {col_type}")
                    print(f"[Database] Added new column: {col_name}")
                except sqlite3.OperationalError:
                    # Kolom sudah ada, skip
                    pass
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def log_login(self, username: str, user_agent: str, model_code: str,
                  brand: str = None, marketing_name: str = None,
                  price_idr: int = 0, os_type: str = None,
                  os_version: str = None, browser: str = None,
                  ip_address: str = None,
                  # Parameter baru untuk fitur price scraping
                  scraped_price_min: int = None,
                  scraped_price_max: int = None,
                  price_source: str = 'none',
                  tokopedia_url: str = None) -> int:
        """
        ====================================================================
        LOG LOGIN - Menyimpan log login user ke database
        ====================================================================
        
        Method ini dipanggil setiap kali ada user yang login ke captive portal.
        Semua informasi tentang user dan device mereka akan disimpan.
        
        ALUR KERJA:
        1. Terima parameter dari routes.py
        2. Insert data ke tabel login_logs
        3. Return ID record yang baru dibuat
        
        Args:
            username: Username yang diinput user saat login
            user_agent: Raw User-Agent string dari browser
            model_code: Kode model perangkat (contoh: SM-S911B)
            brand: Merek perangkat (contoh: Samsung, Apple, Xiaomi)
            marketing_name: Nama marketing (contoh: Galaxy S24, iPhone 15)
            price_idr: Harga dari database lokal (CSV)
            os_type: Tipe sistem operasi (android, ios, windows, dll)
            os_version: Versi OS (contoh: 14.0, 17.1.2)
            browser: Browser yang digunakan (Chrome, Safari, dll)
            ip_address: IP address user
            
            --- PARAMETER BARU (Price Scraping) ---
            scraped_price_min: Harga minimum dari Tokopedia
            scraped_price_max: Harga maksimum dari Tokopedia
            price_source: Sumber harga ('database', 'tokopedia', 'none')
            tokopedia_url: URL pencarian di Tokopedia
        
        Returns:
            int: ID record yang baru dibuat
        
        Example:
            >>> db = LoginDatabase("database/wifi_devices.db")
            >>> record_id = db.log_login(
            ...     username="john_doe",
            ...     user_agent="Mozilla/5.0 (Linux; Android 14; SM-S911B)...",
            ...     model_code="SM-S911B",
            ...     brand="Samsung",
            ...     marketing_name="Galaxy S24",
            ...     price_idr=15000000,
            ...     scraped_price_min=14500000,
            ...     scraped_price_max=16000000,
            ...     price_source="tokopedia",
            ...     tokopedia_url="https://tokopedia.com/search?q=..."
            ... )
            >>> print(f"Login logged with ID: {record_id}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert semua data ke database
            # Kolom baru untuk scraped price ditambahkan di akhir
            cursor.execute('''
                INSERT INTO login_logs 
                (username, user_agent, model_code, brand, marketing_name,
                 price_idr, os_type, os_version, browser, ip_address,
                 scraped_price_min, scraped_price_max, price_source, tokopedia_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, user_agent, model_code, brand, marketing_name,
                  price_idr, os_type, os_version, browser, ip_address,
                  scraped_price_min, scraped_price_max, price_source, tokopedia_url))
            
            conn.commit()
            
            # Return ID record yang baru dibuat
            record_id = cursor.lastrowid
            print(f"[Database] Logged login for '{username}' with ID {record_id}")
            return record_id
    
    def get_all_logs(self, limit: int = 100) -> List[Dict]:
        """Get all login logs"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM login_logs 
                ORDER BY login_time DESC 
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_device_summary(self) -> List[Dict]:
        """Get summary of devices grouped by marketing name"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    brand,
                    marketing_name,
                    model_code,
                    price_idr,
                    COUNT(*) as login_count,
                    COUNT(DISTINCT username) as unique_users
                FROM login_logs
                WHERE marketing_name IS NOT NULL AND marketing_name != ''
                GROUP BY brand, marketing_name
                ORDER BY login_count DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_brand_summary(self) -> List[Dict]:
        """Get summary grouped by brand"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    brand,
                    COUNT(*) as login_count,
                    COUNT(DISTINCT username) as unique_users,
                    COUNT(DISTINCT marketing_name) as device_models,
                    SUM(price_idr) as total_value
                FROM login_logs
                WHERE brand IS NOT NULL AND brand != ''
                GROUP BY brand
                ORDER BY login_count DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get overall statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total logins
            cursor.execute('SELECT COUNT(*) as count FROM login_logs')
            total_logins = cursor.fetchone()['count']
            
            # Unique users
            cursor.execute('SELECT COUNT(DISTINCT username) as count FROM login_logs')
            unique_users = cursor.fetchone()['count']
            
            # Unique devices
            cursor.execute('SELECT COUNT(DISTINCT model_code) as count FROM login_logs WHERE model_code IS NOT NULL')
            unique_devices = cursor.fetchone()['count']
            
            # Total estimated value
            cursor.execute('SELECT SUM(price_idr) as total FROM login_logs')
            total_value = cursor.fetchone()['total'] or 0
            
            # By OS type
            cursor.execute('''
                SELECT os_type, COUNT(*) as count 
                FROM login_logs 
                GROUP BY os_type
            ''')
            os_breakdown = {row['os_type']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total_logins': total_logins,
                'unique_users': unique_users,
                'unique_devices': unique_devices,
                'total_estimated_value': total_value,
                'os_breakdown': os_breakdown
            }
    
    def clear_logs(self) -> int:
        """Clear all logs, returns count of deleted rows"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM login_logs')
            count = cursor.fetchone()['count']
            cursor.execute('DELETE FROM login_logs')
            conn.commit()
            return count

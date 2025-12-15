"""
SQLite Models for storing login logs
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager


class LoginDatabase:
    """SQLite database for storing login logs"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Login logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    user_agent TEXT,
                    model_code TEXT,
                    brand TEXT,
                    marketing_name TEXT,
                    price_idr INTEGER DEFAULT 0,
                    os_type TEXT,
                    os_version TEXT,
                    browser TEXT,
                    ip_address TEXT,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_login_time ON login_logs(login_time)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_brand ON login_logs(brand)
            ''')
            
            conn.commit()
    
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
                  ip_address: str = None) -> int:
        """
        Log a user login
        
        Returns:
            ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO login_logs 
                (username, user_agent, model_code, brand, marketing_name,
                 price_idr, os_type, os_version, browser, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, user_agent, model_code, brand, marketing_name,
                  price_idr, os_type, os_version, browser, ip_address))
            conn.commit()
            return cursor.lastrowid
    
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

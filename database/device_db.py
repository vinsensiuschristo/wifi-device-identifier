"""
Device Database - Load and match device information from CSV files
"""
import csv
import os
from dataclasses import dataclass
from typing import Optional, List, Dict
from difflib import SequenceMatcher


@dataclass
class DeviceInfo:
    """Device information from database"""
    brand: str
    model_code: str
    marketing_name: str
    price_idr: int = 0
    year: int = 2025


class DeviceDatabase:
    """Manage device and pricing database"""
    
    def __init__(self, devices_csv: str, prices_csv: str = None):
        """
        Initialize device database
        
        Args:
            devices_csv: Path to devices CSV (Brand, Model_Code, Marketing_Name)
            prices_csv: Path to prices CSV (Brand, Marketing_Name, Price_IDR, Year)
        """
        self.devices_csv = devices_csv
        self.prices_csv = prices_csv
        
        # Data storage
        self.devices: Dict[str, DeviceInfo] = {}  # model_code -> DeviceInfo
        self.prices: Dict[str, int] = {}  # marketing_name -> price
        
        self._load_devices()
        if prices_csv:
            self._load_prices()
    
    def _load_devices(self) -> None:
        """Load devices from CSV file"""
        if not os.path.exists(self.devices_csv):
            print(f"[!] Devices CSV not found: {self.devices_csv}")
            return
        
        try:
            with open(self.devices_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    brand = row.get('Brand', '').strip()
                    model_code = row.get('Model_Code', '').strip()
                    marketing_name = row.get('Marketing_Name', '').strip()
                    
                    if model_code:
                        self.devices[model_code.upper()] = DeviceInfo(
                            brand=brand,
                            model_code=model_code,
                            marketing_name=marketing_name or model_code
                        )
                        
                        # Also store lowercase and original for flexible matching
                        self.devices[model_code.lower()] = self.devices[model_code.upper()]
                        self.devices[model_code] = self.devices[model_code.upper()]
            
            print(f"[+] Loaded {len(self.devices) // 3} devices from database")
        except Exception as e:
            print(f"[-] Error loading devices: {e}")
    
    def _load_prices(self) -> None:
        """Load prices from CSV file"""
        if not self.prices_csv or not os.path.exists(self.prices_csv):
            print(f"[!] Prices CSV not found: {self.prices_csv}")
            return
        
        try:
            with open(self.prices_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    marketing_name = row.get('Marketing_Name', '').strip()
                    price_str = row.get('Price_IDR', '0').strip()
                    
                    # Clean price string
                    price = int(price_str.replace('.', '').replace(',', '').replace('Rp', '').strip() or 0)
                    
                    if marketing_name:
                        self.prices[marketing_name.lower()] = price
            
            # Update device prices
            for model_code, device in self.devices.items():
                if device.marketing_name.lower() in self.prices:
                    device.price_idr = self.prices[device.marketing_name.lower()]
            
            print(f"[+] Loaded {len(self.prices)} prices from database")
        except Exception as e:
            print(f"[-] Error loading prices: {e}")
    
    def find_device(self, model_code: str) -> Optional[DeviceInfo]:
        """
        Find device by model code (exact match)
        
        Args:
            model_code: Device model code (e.g., SM-S911B)
            
        Returns:
            DeviceInfo if found, None otherwise
        """
        if not model_code:
            return None
        
        # Try exact match
        if model_code in self.devices:
            return self.devices[model_code]
        
        # Try uppercase
        if model_code.upper() in self.devices:
            return self.devices[model_code.upper()]
        
        # Try lowercase
        if model_code.lower() in self.devices:
            return self.devices[model_code.lower()]
        
        return None
    
    def search_device(self, query: str, threshold: float = 0.6) -> Optional[DeviceInfo]:
        """
        Search for device using fuzzy matching
        
        Args:
            query: Search query (model code or marketing name)
            threshold: Minimum similarity score (0-1)
            
        Returns:
            Best matching DeviceInfo if above threshold
        """
        if not query:
            return None
        
        # First try exact match
        exact = self.find_device(query)
        if exact:
            return exact
        
        # Fuzzy search
        query_lower = query.lower()
        best_match = None
        best_score = 0.0
        
        seen_devices = set()
        for model_code, device in self.devices.items():
            # Skip duplicates
            device_key = (device.brand, device.model_code)
            if device_key in seen_devices:
                continue
            seen_devices.add(device_key)
            
            # Compare with model code
            score1 = SequenceMatcher(None, query_lower, model_code.lower()).ratio()
            
            # Compare with marketing name
            score2 = SequenceMatcher(None, query_lower, device.marketing_name.lower()).ratio()
            
            score = max(score1, score2)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = device
        
        return best_match
    
    def get_price(self, marketing_name: str) -> int:
        """Get price by marketing name"""
        if not marketing_name:
            return 0
        return self.prices.get(marketing_name.lower(), 0)
    
    def get_all_brands(self) -> List[str]:
        """Get list of all unique brands"""
        brands = set()
        for device in self.devices.values():
            if device.brand:
                brands.add(device.brand)
        return sorted(list(brands))
    
    def get_devices_by_brand(self, brand: str) -> List[DeviceInfo]:
        """Get all devices for a brand"""
        result = []
        seen = set()
        
        for device in self.devices.values():
            if device.brand.lower() == brand.lower():
                if device.model_code not in seen:
                    seen.add(device.model_code)
                    result.append(device)
        
        return result
    
    def stats(self) -> Dict:
        """Get database statistics"""
        unique_devices = len(set((d.brand, d.model_code) for d in self.devices.values()))
        unique_brands = len(self.get_all_brands())
        devices_with_price = sum(1 for d in self.devices.values() if d.price_idr > 0)
        
        return {
            'total_devices': unique_devices,
            'total_brands': unique_brands,
            'devices_with_price': devices_with_price // 3,  # Account for duplicates
            'total_prices': len(self.prices)
        }

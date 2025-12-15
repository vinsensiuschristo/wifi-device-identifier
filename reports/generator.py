"""
Report Generator - Generate reports from login data
"""
import csv
import json
import os
from datetime import datetime
from typing import Dict, List


class ReportGenerator:
    """Generate reports from login database"""
    
    def __init__(self, login_db):
        self.login_db = login_db
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_summary(self) -> Dict:
        """Generate summary report"""
        stats = self.login_db.get_stats()
        device_summary = self.login_db.get_device_summary()
        brand_summary = self.login_db.get_brand_summary()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'by_device': device_summary,
            'by_brand': brand_summary
        }
    
    def export_csv(self, filename: str = None) -> str:
        """Export logs to CSV file"""
        if filename is None:
            filename = f"device_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        logs = self.login_db.get_all_logs(limit=10000)
        
        if not logs:
            return filepath
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=logs[0].keys())
            writer.writeheader()
            writer.writerows(logs)
        
        return filepath
    
    def export_json(self, filename: str = None) -> str:
        """Export report to JSON file"""
        if filename is None:
            filename = f"device_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        report = self.generate_summary()
        report['logs'] = self.login_db.get_all_logs(limit=10000)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
    
    def format_price_idr(self, price: int) -> str:
        """Format price in Indonesian Rupiah"""
        if price == 0:
            return "-"
        return f"Rp {price:,.0f}".replace(',', '.')
    
    def get_top_devices(self, limit: int = 10) -> List[Dict]:
        """Get top devices by login count"""
        summary = self.login_db.get_device_summary()
        return summary[:limit]
    
    def get_value_report(self) -> Dict:
        """Get total value report"""
        stats = self.login_db.get_stats()
        brand_summary = self.login_db.get_brand_summary()
        
        return {
            'total_logins': stats['total_logins'],
            'total_estimated_value': stats['total_estimated_value'],
            'formatted_value': self.format_price_idr(stats['total_estimated_value']),
            'by_brand': [
                {
                    'brand': b['brand'],
                    'count': b['login_count'],
                    'value': b['total_value'],
                    'formatted_value': self.format_price_idr(b['total_value'] or 0)
                }
                for b in brand_summary
            ]
        }

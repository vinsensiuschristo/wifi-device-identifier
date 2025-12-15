"""
Download complete device database from Google Play supported devices
"""
import requests
import csv
import io
import os

# URL Resmi Google
URL = "http://storage.googleapis.com/play_public/supported_devices.csv"
OUTPUT_FILE = "data/devices.csv"

def download_and_save_data():
    print("🚀 Memulai proses...")
    
    current_folder = os.path.dirname(os.path.abspath(__file__))
    print(f"📂 File akan disimpan di folder: {current_folder}")
    
    try:
        print("⏳ Sedang mendownload data dari Google (mohon tunggu)...")
        response = requests.get(URL, timeout=60)
        response.raise_for_status()
        
        content = response.content.decode('utf-16')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        print("✅ Download selesai! Sedang menulis ke file CSV...")
        
        count = 0
        file_path = os.path.join(current_folder, OUTPUT_FILE)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Brand', 'Model_Code', 'Marketing_Name'])
            
            for row in csv_reader:
                brand = row.get('Retail Branding', '').strip()
                marketing_name = row.get('Marketing Name', '').strip()
                model_code = row.get('Model', '').strip()
                
                if brand and marketing_name and model_code:
                    writer.writerow([brand, model_code, marketing_name])
                    count += 1
        
        print("-" * 30)
        print(f"🎉 SUKSES! File berhasil dibuat: {OUTPUT_FILE}")
        print(f"📊 Total data: {count} baris")
        print(f"📍 Lokasi file lengkap: {file_path}")
        print("-" * 30)

        if os.path.exists(file_path):
            print("✅ Verifikasi sistem: File DITEMUKAN di disk.")
        else:
            print("❌ Verifikasi sistem: File TIDAK DITEMUKAN.")

    except Exception as e:
        print(f"❌ Terjadi error: {e}")

download_and_save_data()

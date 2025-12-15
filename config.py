"""
Configuration for WiFi Device Identifier
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Flask Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "wifi-device-secret-key-2025")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Database paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEVICES_CSV = os.path.join(DATA_DIR, "devices.csv")
PRICES_CSV = os.path.join(DATA_DIR, "prices.csv")
DATABASE_PATH = os.path.join(BASE_DIR, "database", "wifi_devices.db")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

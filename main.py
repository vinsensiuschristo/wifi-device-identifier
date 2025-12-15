"""
WiFi Device Identifier - Main Entry Point
"""
from flask import Flask
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config


def create_app():
    """Create Flask application"""
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    print("\n" + "="*50)
    print("🌐 WiFi Device Identifier")
    print("="*50)
    print(f"📍 Login Page:   http://localhost:5000/login")
    print(f"📊 Dashboard:    http://localhost:5000/dashboard")
    print(f"🔌 API Devices:  http://localhost:5000/api/devices")
    print(f"📋 API Report:   http://localhost:5000/api/report")
    print(f"🧪 Test UA:      http://localhost:5000/api/test-ua")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=config.DEBUG)

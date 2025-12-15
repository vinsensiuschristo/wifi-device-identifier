"""
Flask Routes for WiFi Device Identifier
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, make_response
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.user_agent import UserAgentParser
from database.device_db import DeviceDatabase
from database.models import LoginDatabase
from reports.generator import ReportGenerator
import config

# Initialize components
ua_parser = UserAgentParser()
device_db = DeviceDatabase(config.DEVICES_CSV, config.PRICES_CSV)
login_db = LoginDatabase(config.DATABASE_PATH)
report_gen = ReportGenerator(login_db)

# Create blueprint
main = Blueprint('main', __name__)


@main.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('main.login'))


@main.route('/login', methods=['GET', 'POST'])
def login():
    """
    Captive Portal Login Page
    - GET: Show login form (with Client Hints request headers)
    - POST: Process login, capture User-Agent + Client Hints, identify device
    """
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # Get User-Agent from request
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        
        # Get Client Hints (Chrome 90+)
        # These headers provide more accurate device info than User-Agent
        ch_model = request.headers.get('Sec-CH-UA-Model', '')
        ch_platform = request.headers.get('Sec-CH-UA-Platform', '')
        ch_platform_version = request.headers.get('Sec-CH-UA-Platform-Version', '')
        ch_mobile = request.headers.get('Sec-CH-UA-Mobile', '')
        ch_full_version = request.headers.get('Sec-CH-UA-Full-Version-List', '')
        
        # Parse User-Agent
        parsed = ua_parser.parse(user_agent)
        
        # Override model_code with Client Hints if available
        if ch_model and ch_model.strip('"'):
            parsed.model_code = ch_model.strip('"')
        
        # Find device in database - EXACT MATCH ONLY (no fuzzy to avoid wrong matches)
        device = None
        model_codes = [parsed.model_code] if parsed.model_code else []
        model_codes.extend(ua_parser.extract_model_codes(user_agent))
        
        for code in model_codes:
            if code and code != 'K' and code != 'Android Device':  # Skip placeholders
                device = device_db.find_device(code)
                if device:
                    break
        
        # Note: Fuzzy search disabled to prevent wrong matches like 2201117PG -> 2201117TG
        
        # Build extended user agent info for logging
        extended_ua = user_agent
        if ch_model:
            extended_ua += f" [CH-Model: {ch_model}]"
        
        # Log the login
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
            ip_address=ip_address
        )
        
        # Return success page
        return render_template('login_success.html',
            username=username,
            device=device,
            parsed=parsed,
            client_hints={
                'model': ch_model,
                'platform': ch_platform,
                'platform_version': ch_platform_version,
                'mobile': ch_mobile
            }
        )
    
    # GET - Show login form with Client Hints request headers
    response = make_response(render_template('login.html'))
    
    # Request Client Hints from browser
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
    """API: Get report summary"""
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
    """API: Export report to CSV or JSON"""
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
    """API: Test User-Agent parsing (for debugging)"""
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
    """API: Clear all logs"""
    count = login_db.clear_logs()
    return jsonify({
        'success': True,
        'deleted': count
    })

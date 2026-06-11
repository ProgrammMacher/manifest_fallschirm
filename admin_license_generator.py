#!/usr/bin/env python3
"""
Standalone License Key Generator UI
- Simple Flask web app for generating machine-bound license keys
- No authentication (use only on trusted networks)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.license.generate_license_key import generate_license_key

app = Flask(__name__, template_folder='templates')
app.config['JSON_SORT_KEYS'] = False

@app.route('/', methods=['GET'])
def index():
    """Main page with license key generator form"""
    return render_template('license_generator.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    """API endpoint to generate license key"""
    try:
        data = request.json
        
        # Validate inputs
        customer = data.get('customer', '').strip()
        fingerprint = data.get('fingerprint', '').strip()
        tier = data.get('tier', '3m').strip()
        
        if not customer:
            return jsonify({'error': 'Kundenname erforderlich'}), 400
        
        if not fingerprint:
            return jsonify({'error': 'Fingerprint erforderlich'}), 400
        
        if len(fingerprint) != 64:
            return jsonify({'error': 'Fingerprint muss 64 Zeichen lang sein'}), 400
        
        if tier not in ['3m', '12m', 'unlimited']:
            return jsonify({'error': 'Ungültige Lizenzstufe'}), 400
        
        # Generate license key
        license_key = generate_license_key(
            customer=customer,
            fingerprint=fingerprint,
            tier=tier
        )
        
        # Parse key to show metadata
        parts = license_key.split('.')
        if len(parts) >= 2:
            try:
                import base64
                payload_b64 = parts[1]
                # Add padding if needed
                padding = 4 - (len(payload_b64) % 4)
                if padding != 4:
                    payload_b64 += '=' * padding
                payload_json = base64.urlsafe_b64decode(payload_b64).decode()
                payload = json.loads(payload_json)
            except:
                payload = {}
        else:
            payload = {}
        
        # Calculate expiry date
        if tier == '3m':
            exp_date = (datetime.now() + timedelta(days=90)).strftime('%d.%m.%Y')
        elif tier == '12m':
            exp_date = (datetime.now() + timedelta(days=365)).strftime('%d.%m.%Y')
        else:
            exp_date = 'Unbegrenzt'
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'customer': customer,
            'tier': tier,
            'exp_date': exp_date,
            'fingerprint': fingerprint,
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        })
    
    except Exception as e:
        return jsonify({'error': f'Fehler: {str(e)}'}), 500

@app.route('/api/info', methods=['GET'])
def info():
    """API endpoint for app info"""
    return jsonify({
        'version': '1.0',
        'app': 'Manifest Fallschirm License Generator',
        'tiers': {
            '3m': '3 Monate (90 Tage)',
            '12m': '12 Monate (365 Tage)',
            'unlimited': 'Unbegrenzt'
        }
    })

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  Manifest Fallschirm License Key Generator                    ║
║  http://localhost:5555                                        ║
║                                                               ║
║  ⚠️  Nur auf vertrauenswürdigen Netzwerken verwenden!         ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='127.0.0.1', port=5555, debug=False)

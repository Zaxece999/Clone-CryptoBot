from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import time
import threading
import asyncio
from simple_bot_db import get_user_balances_from_bot_db, check_bot_db_connection, map_telegram_to_internal_user_id
import sqlite3
import json
import requests
import subprocess
import sys
import asyncio
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

app.config['STATIC_FOLDER'] = 'static'
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['STATIC_FOLDER'], 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/deposit')
def deposit():
    return render_template('deposit.html')

@app.route('/withdraw')
def withdraw():
    return render_template('withdraw.html')

@app.route('/swap')
def swap():
    return render_template('swap.html')

@app.route('/settings')
def settings():
    user_id = request.args.get('user_id', '1')
    return render_template('settings.html', user_id=user_id)

@app.route('/timezones')
def timezones():
    return render_template('timezones.html')

@app.route('/language')
def language():
    return render_template('language.html')

@app.route('/api/settings/timezone', methods=['POST'])
def update_timezone():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        timezone = data.get('timezone')

        if not user_id or not timezone:
            return jsonify({'error': 'User ID and timezone are required'}), 400

        result = update_user_settings(user_id, 'timezone', timezone)

        if result:
            return jsonify({'success': True, 'message': 'Timezone updated successfully'})
        else:
            return jsonify({'error': 'Failed to update timezone'}), 500

    except Exception as e:
        print(f"Error updating timezone: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/settings/language', methods=['POST'])
def update_language():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        language = data.get('language')

        if not user_id or not language:
            return jsonify({'error': 'User ID and language are required'}), 400

        result = update_user_settings(user_id, 'language', language)

        if result:
            return jsonify({'success': True, 'message': 'Language updated successfully'})
        else:
            return jsonify({'error': 'Failed to update language'}), 500

    except Exception as e:
        print(f"Error updating language: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/settings/currency', methods=['POST'])
def update_currency():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        currency = data.get('currency')

        if not user_id or not currency:
            return jsonify({'error': 'User ID and currency are required'}), 400

        result = update_user_settings(user_id, 'currency', currency)

        if result:
            return jsonify({'success': True, 'message': 'Currency updated successfully'})
        else:
            return jsonify({'error': 'Failed to update currency'}), 500

    except Exception as e:
        print(f"Error updating currency: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/settings/sounds', methods=['POST'])
def update_sounds():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        sounds_enabled = data.get('sounds_enabled')

        if not user_id or sounds_enabled is None:
            return jsonify({'error': 'User ID and sounds_enabled are required'}), 400

        result = update_user_settings(user_id, 'sounds_enabled', sounds_enabled)

        if result:
            return jsonify({'success': True, 'message': 'Sounds setting updated successfully'})
        else:
            return jsonify({'error': 'Failed to update sounds setting'}), 500

    except Exception as e:
        print(f"Error updating sounds setting: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/settings/get', methods=['GET'])
def get_user_settings():
    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        conn = sqlite3.connect('cryptobot.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT timezone, local_currency, bot_language
            FROM user_settings
            WHERE user_id = ?
        ''', (user_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            timezone, currency, language = result
            return jsonify({
                'success': True,
                'settings': {
                    'timezone': timezone or 'UTC',
                    'language': language or 'ru',
                    'currency': currency or 'USD',
                    'sounds_enabled': True
                }
            })
        else:
            return jsonify({
                'success': True,
                'settings': {
                    'timezone': 'UTC',
                    'language': 'ru',
                    'currency': 'USD',
                    'sounds_enabled': True
                }
            })

    except Exception as e:
        print(f"Error getting user settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/address_book')
def address_book():
    return render_template('address_book.html')

@app.route('/security')
def security():
    return render_template('security.html')

@app.route('/update_info')
def update_info():
    return render_template('update_info.html')

@app.route('/currency_selection')
def currency_selection():
    return render_template('currency_selection.html')

@app.route('/user_menu')
def user_menu():
    return render_template('user_menu.html')

@app.route('/p2p_merchant')
def p2p_merchant():
    return render_template('p2p_merchant.html')

@app.route('/p2c_merchant')
def p2c_merchant():
    return render_template('p2c_merchant.html')

@app.route('/verification')
def verification():
    return render_template('verification.html')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/aml_policy')
def aml_policy():
    return render_template('aml_policy.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('static/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('static/images', filename)

@app.route('/icons/<path:filename>')
def serve_icons(filename):
    return send_from_directory('static/icons', filename)

@app.route('/api/verification/update', methods=['POST'])
def update_verification_status():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        status = data.get('status')
        verification_data = data.get('data', {})

        if not user_id or not status:
            return jsonify({'error': 'Missing required fields'}), 400

        result = update_user_verification_status(user_id, status, verification_data)

        if result:
            return jsonify({'success': True, 'message': 'Verification status updated'})
        else:
            return jsonify({'error': 'Failed to update verification status'}), 500

    except Exception as e:
        print(f"Error updating verification status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/verification/status/<user_id>')
def get_verification_status(user_id):
    try:
        status = get_user_verification_status(user_id)
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        print(f"Error getting verification status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/verification/upload-documents', methods=['POST'])
def upload_verification_documents():
    try:
        user_id = request.form.get('user_id')
        front_file = request.files.get('front_document')
        back_file = request.files.get('back_document')

        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        if not front_file or not back_file:
            return jsonify({'error': 'Both front_document and back_document are required'}), 400

        allowed = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}
        if front_file.mimetype not in allowed or back_file.mimetype not in allowed:
            return jsonify({'error': 'Only image files are allowed'}), 400

        user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        front_name = 'front_' + secure_filename(front_file.filename or 'document')
        back_name = 'back_' + secure_filename(back_file.filename or 'document')
        front_path = os.path.join(user_dir, front_name)
        back_path = os.path.join(user_dir, back_name)
        front_file.save(front_path)
        back_file.save(back_path)

        front_rel = os.path.relpath(front_path, app.config['STATIC_FOLDER'])
        back_rel = os.path.relpath(back_path, app.config['STATIC_FOLDER'])

        updated = update_user_verification_status(user_id, 'documents_uploaded', {
            'front_document': front_rel,
            'back_document': back_rel,
        })
        if not updated:
            return jsonify({'error': 'Failed to update verification status'}), 500

        update_user_verification_status(user_id, 'documents_verification_pending', {})

        return jsonify({'success': True, 'front_document': front_rel, 'back_document': back_rel})
    except Exception as e:
        print(f"Error uploading documents: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/cursors/<path:filename>')
def serve_cursors(filename):
    return send_from_directory('static/cursors', filename)

@app.route('/fonts/<path:filename>')
def serve_fonts(filename):
    return send_from_directory('static/fonts', filename)

@app.route('/gift/<path:filename>')
def serve_gift_images(filename):
    return send_from_directory('.', filename)


CRYPTO_IDS = {
    'USDT': 'tether',
    'TON': 'the-open-network',
    'SOL': 'solana',
    'TRX': 'tron',
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'DOGE': 'dogecoin',
    'LTC': 'litecoin',
    'BNB': 'binancecoin',
    'USDC': 'usd-coin',
    'NOT': None,
    'TRUMP': None,
    'MELANIA': None,
    'WIF': 'dogwifhat',
    'BONK': 'bonk',
}

SUPPORTED_FIATS = ['USD','EUR','RUB','BYN','UAH','GBP','CNY','KZT','UZS','GEL','TRY','AMD','THB','INR','BRL','IDR','AZN','AED','PLN','ILS','KGS','TJS']

COINGECKO_API_KEY = os.environ.get('COINGECKO_API_KEY', '')
OPENEXCHANGERATES_APP_ID = os.environ.get('OPENEXCHANGERATES_APP_ID', '')
COINMARKETCAP_API_KEY = os.environ.get('COINMARKETCAP_API_KEY', '')

_cache_lock = threading.Lock()
_cache = {
    'crypto_prices': {
        'data': {},
        'ts': 0,
        'ttl': 60
    },
    'fiat_currency_symbols': {
        'data': [],
        'ts': 0,
        'ttl': 86400
    },
    'user_settings': {
        'data': {'base_currency': 'USD'},
        'ts': 0,
        'ttl': 3600
    },
    'fiat_pair_rates': {
        'data': {},
        'ts': 0,
        'ttl': 1800
    }
}

_user_balances_lock = threading.Lock()
_user_balances = {
 'USDT': 0.0,
 'TON': 0.0,
 'SOL': 0.0,
 'TRX': 0.0,
 'BTC': 0.0,
 'ETH': 0.0,
 'DOGE': 0.0,
 'LTC': 0.0,
 'BNB': 0.0,
 'USDC': 0.0,
 'NOT': 0.0,
 'TRUMP': 0.0,
 'MELANIA': 0.0,
 'WIF': 0.0,
 'BONK': 0.0
}

_user_profiles_lock = threading.Lock()
_user_profiles = {}

_demo_user_balances_lock = threading.Lock()
_demo_user_balances = {}

_synced_user_balances_lock = threading.Lock()
_synced_user_balances = {}
def _cached_fetch(name: str, fetch_func):
    with _cache_lock:
        bucket = _cache[name]
        now = time.time()
        if now - bucket['ts'] < bucket['ttl'] and bucket['data']:
            return bucket['data']
    data = fetch_func()
    with _cache_lock:
        _cache[name]['data'] = data or _cache[name]['data']
        _cache[name]['ts'] = time.time()
        return _cache[name]['data']


def _fetch_crypto_prices_usd():
    all_crypto_symbols = list(_user_balances.keys())

    current_prices = {
        'USDT': 1.0,
        'TON': 3.15,
        'SOL': 205.66,
        'TRX': 0.34,
        'BTC': 110632.0,
        'ETH': 4281.08,
        'DOGE': 0.21,
        'LTC': 110.08,
        'BNB': 849.44,
        'USDC': 1.0,
        'NOT': 0.01,
        'TRUMP': 0.1,
        'MELANIA': 0.05,
        'WIF': 2.0,
        'BONK': 0.00002
    }

    if COINMARKETCAP_API_KEY:
        try:
            symbols_param = ','.join(sorted(set(all_crypto_symbols)))
            cmc_url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={symbols_param}&convert=USD'
            headers = { 'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY }
            print(f"Получение курсов криптовалют от CoinMarketCap для символов: {symbols_param}")
            print(f"CoinMarketCap API ключ: {COINMARKETCAP_API_KEY[:10]}...")
            r = requests.get(cmc_url, headers=headers, timeout=10)
            print(f"Статус ответа CoinMarketCap: {r.status_code}")
            r.raise_for_status()
            data = r.json()
            print(f"Ключи ответа CoinMarketCap: {list(data.keys()) if isinstance(data, dict) else 'Не словарь'}")

            out = {}
            changes = {}
            d = data.get('data', {})
            for sym in all_crypto_symbols:
                info = d.get(sym)
                if isinstance(info, dict):
                    quote = ((info.get('quote') or {}).get('USD') or {})
                    price = quote.get('price')
                    ch24 = quote.get('percent_change_24h')
                    if isinstance(price, (int, float)):
                        out[sym] = float(price)
                        changes[sym] = float(ch24) if isinstance(ch24, (int, float)) else 0.0
                        continue
                out[sym] = current_prices.get(sym, 0.0)
                changes[sym] = 0.0
            out['USDT'] = 1.0
            print(f"Курсы CoinMarketCap успешно получены: {len(out)} символов")
            with _cache_lock:
                _cache.setdefault('crypto_changes', {'data': {}, 'ts': 0, 'ttl': 25})
                _cache['crypto_changes']['data'] = changes
                _cache['crypto_changes']['ts'] = time.time()
            return out
        except Exception as e:
            print(f"Ошибка получения курсов от CoinMarketCap: {e}")
            print(f"Использованный CoinMarketCap API ключ: {COINMARKETCAP_API_KEY[:10]}...")

    try:
        ids_to_fetch = [CRYPTO_IDS[sym] for sym in all_crypto_symbols if sym in CRYPTO_IDS and CRYPTO_IDS[sym] is not None]
        ids_param = ','.join(ids_to_fetch)
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd&include_24hr_change=true'
        headers = {}
        if COINGECKO_API_KEY and COINGECKO_API_KEY != 'YOUR_COINGECKO_API_KEY':
            headers['x-cg-pro-api-key'] = COINGECKO_API_KEY
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        out = {}
        changes = {}
        for sym in all_crypto_symbols:
            cid = CRYPTO_IDS.get(sym)
            if cid and cid in data and 'usd' in data[cid]:
                out[sym] = float(data[cid]['usd'])
                ch = data[cid].get('usd_24h_change')
                try:
                    changes[sym] = float(ch) if ch is not None else 0.0
                except Exception:
                    changes[sym] = 0.0
            else:
                out[sym] = current_prices.get(sym, 0.0)
                changes[sym] = 0.0
        out['USDT'] = 1.0
        with _cache_lock:
            _cache.setdefault('crypto_changes', {'data': {}, 'ts': 0, 'ttl': 25})
            _cache['crypto_changes']['data'] = changes
            _cache['crypto_changes']['ts'] = time.time()
        return out
    except Exception as e:
        print(f"Ошибка получения курсов от CoinGecko: {e}")

    with _cache_lock:
        _cache.setdefault('crypto_changes', {'data': {}, 'ts': 0, 'ttl': 25})
        _cache['crypto_changes']['data'] = {k: 0.0 for k in current_prices.keys()}
        _cache['crypto_changes']['ts'] = time.time()
    return current_prices
def _fetch_fiat_pair_rate(from_code: str, to_code: str) -> float:
    if from_code.upper() == to_code.upper():
        return 1.0

    pair_key = f"{from_code.upper()}->{to_code.upper()}"

    with _cache_lock:
        bucket = _cache['fiat_pair_rates']
        cached = bucket['data'].get(pair_key)
        if cached and (time.time() - cached['ts'] < bucket['ttl']):
            return cached['rate']

    if from_code.upper() not in SUPPORTED_FIATS or to_code.upper() not in SUPPORTED_FIATS:
        return 0.0

    try:
        if OPENEXCHANGERATES_APP_ID:
            print(f"Попытка получения курсов от OpenExchangeRates для {pair_key} с APP_ID: {OPENEXCHANGERATES_APP_ID[:10]}...")
            with _cache_lock:
                oex_rates = _cache['fiat_pair_rates']['data'].get('OEX_USD_BASE')
                oex_rates_ts = oex_rates['ts'] if oex_rates else 0
            if not oex_rates or (time.time() - oex_rates_ts > 1800):
                oex_url = f'https://openexchangerates.org/api/latest.json?app_id={OPENEXCHANGERATES_APP_ID}'
                print(f"Запрос к OpenExchangeRates: {oex_url}")
                r = requests.get(oex_url, timeout=10)
                print(f"Статус ответа OpenExchangeRates: {r.status_code}")
                r.raise_for_status()
                data = r.json()
                print(f"Ключи ответа OpenExchangeRates: {list(data.keys()) if isinstance(data, dict) else 'Не словарь'}")
                rates_map = data.get('rates', {})
                if isinstance(rates_map, dict) and rates_map:
                    print(f"Количество курсов OpenExchangeRates: {len(rates_map)}")
                    with _cache_lock:
                        _cache['fiat_pair_rates']['data']['OEX_USD_BASE'] = {'rates': rates_map, 'ts': time.time()}
                    oex_rates = _cache['fiat_pair_rates']['data']['OEX_USD_BASE']
            rates_map = oex_rates.get('rates', {}) if oex_rates else {}
            usd_to_from = float(rates_map.get(from_code.upper(), 0.0))
            usd_to_to = float(rates_map.get(to_code.upper(), 0.0))
            print(f"Курсы OpenExchangeRates - USD к {from_code}: {usd_to_from}, USD к {to_code}: {usd_to_to}")
            if usd_to_from > 0 and usd_to_to > 0:
                rate = usd_to_to / usd_to_from
                print(f"Рассчитанный курс OpenExchangeRates для {pair_key}: {rate}")
                with _cache_lock:
                    _cache['fiat_pair_rates']['data'][pair_key] = {'rate': rate, 'ts': time.time()}
                return rate
            else:
                print(f"Курсы OpenExchangeRates недоступны для {pair_key}")
        else:
            print("OpenExchangeRates APP_ID не предоставлен")
    except Exception as e:
        print(f"Ошибка OpenExchangeRates для {pair_key}: {e}")

    try:
        ex_url = f'https://api.exchangerate.host/convert?from={from_code.upper()}&to={to_code.upper()}&amount=1'
        r2 = requests.get(ex_url, timeout=10)
        r2.raise_for_status()
        data2 = r2.json()
        rate = float(data2.get('result', 0.0))
        if rate <= 0:
            raise ValueError('Invalid rate from exchangerate.host')
        with _cache_lock:
            _cache['fiat_pair_rates']['data'][pair_key] = {'rate': rate, 'ts': time.time()}
        return rate
    except Exception as e2:
        print(f"exchangerate.host не удался для {pair_key}: {e2}")

    try:
        url = f'https://api.frankfurter.app/latest?amount=1&from={from_code.upper()}&to={to_code.upper()}'
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        rate = float(data.get('rates', {}).get(to_code.upper(), 0.0))
        if rate <= 0:
            raise ValueError('Неверный курс от Frankfurter')
        with _cache_lock:
            _cache['fiat_pair_rates']['data'][pair_key] = {'rate': rate, 'ts': time.time()}
        return rate
    except Exception as e:
        print(f"Frankfurter не удался для {pair_key}: {e}")

    try:
        with _cache_lock:
            usd_rates = _cache['fiat_pair_rates']['data'].get('USD_BASE_RATES')
            usd_rates_ts = usd_rates['ts'] if usd_rates else 0
        if not usd_rates or (time.time() - usd_rates_ts > 3600):
            er_url = 'https://open.er-api.com/v6/latest/USD'
            r3 = requests.get(er_url, timeout=10)
            r3.raise_for_status()
            data3 = r3.json()
            if data3.get('result') == 'success':
                rates_map = data3.get('rates', {})
                with _cache_lock:
                    _cache['fiat_pair_rates']['data']['USD_BASE_RATES'] = {'rates': rates_map, 'ts': time.time()}
                usd_rates = _cache['fiat_pair_rates']['data']['USD_BASE_RATES']
        rates_map = usd_rates.get('rates', {}) if usd_rates else {}
        usd_to_from = float(rates_map.get(from_code.upper(), 0.0))
        usd_to_to = float(rates_map.get(to_code.upper(), 0.0))
        if usd_to_from > 0 and usd_to_to > 0:
            rate = usd_to_to / usd_to_from
            with _cache_lock:
                _cache['fiat_pair_rates']['data'][pair_key] = {'rate': rate, 'ts': time.time()}
            return rate
    except Exception as e3:
        print(f"open.er-api резервный вариант не удался для {pair_key}: {e3}")
    return 0.0


def _convert_currency(from_currency: str, to_currency: str, amount: float):
    from_code = from_currency.upper()
    to_code = to_currency.upper()
    amt = float(amount)
    if amt < 0:
        amt = 0.0

    crypto_prices_usd = _cached_fetch('crypto_prices', _fetch_crypto_prices_usd)

    def is_crypto(code: str) -> bool:
        return code in crypto_prices_usd

    if from_code == to_code:
        return 1.0, amt

    usd_to_to_rate = 1.0
    from_to_usd_rate = 1.0

    if is_crypto(from_code):
        from_to_usd_rate = crypto_prices_usd.get(from_code, 0.0)
    else:
        usd_to_from = _fetch_fiat_pair_rate('USD', from_code)
        if usd_to_from <= 0:
            return 0.0, 0.0
        from_to_usd_rate = 1.0 / usd_to_from

    if is_crypto(to_code):
        to_price_usd = crypto_prices_usd.get(to_code, 0.0)
        if to_price_usd <= 0:
            return 0.0, 0.0
        usd_to_to_rate = 1.0 / to_price_usd
    else:
        usd_to_to_rate = _fetch_fiat_pair_rate('USD', to_code)
        if usd_to_to_rate <= 0:
            return 0.0, 0.0

    rate = from_to_usd_rate * usd_to_to_rate
    converted = amt * rate
    return rate, converted


def _fetch_all_fiat_currency_symbols():
    url = 'https://api.frankfurter.app/currencies'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return sorted(list(data.keys()))
    except Exception as e:
        print(f"Error fetching all fiat currency symbols from Frankfurter: {e}")
        return ['USD', 'EUR', 'RUB', 'BYN', 'UAH', 'GBP', 'CNY', 'KZT', 'UZS', 'GEL', 'TRY', 'AMD', 'THB', 'INR', 'BRL', 'IDR', 'AZN', 'AED', 'PLN', 'ILS', 'KGS', 'TJS']


@app.route('/api/crypto/prices')
def api_crypto_prices():
    data = _cached_fetch('crypto_prices', _fetch_crypto_prices_usd)
    with _cache_lock:
        changes = _cache.get('crypto_changes', {}).get('data', {})
    symbols_param = request.args.get('symbols')
    if symbols_param:
        symbols = {s.strip().upper() for s in symbols_param.split(',')}
        data = {k: v for k, v in data.items() if k in symbols}
        changes = {k: changes.get(k, 0.0) for k in symbols}
    return jsonify({'prices_usd': data, 'changes_24h_pct': changes, 'status': 'success'})


@app.route('/api/fiat/currencies')
def api_fiat_currencies():
    currencies = _cached_fetch('fiat_currency_symbols', _fetch_all_fiat_currency_symbols)
    return jsonify({'currencies': currencies, 'status': 'success'})

@app.route('/api/fiat/usd_rates')
def api_fiat_usd_rates():
    rates = {}
    for code in SUPPORTED_FIATS:
        if code == 'USD':
            rates['USD'] = 1.0
            continue
        rate = _fetch_fiat_pair_rate('USD', code)
        if rate > 0:
            rates[code] = rate
    return jsonify({'base': 'USD', 'rates': rates, 'status': 'success'})


@app.route('/api/currencies')
def api_currencies():
    fiat_codes = ['USD','EUR','RUB','BYN','UAH','GBP','CNY','KZT','UZS','GEL','TRY','AMD','THB','INR','BRL','IDR','AZN','AED','PLN','ILS','KGS','TJS']
    fiat_symbols = {
        'USD': '$', 'EUR': '€', 'RUB': '₽', 'BYN': 'Br', 'UAH': '₴', 'GBP': '£', 'CNY': '¥',
        'KZT': '₸', 'UZS': "сум", 'GEL': '₾', 'TRY': '₺', 'AMD': '֏', 'THB': '฿', 'INR': '₹',
        'BRL': 'R$', 'IDR': 'Rp', 'AZN': '₼', 'AED': 'د.إ', 'PLN': 'zł', 'ILS': '₪', 'KGS': 'сом', 'TJS': 'ЅМ'
    }
    fiat_list = [{ 'code': c, 'name': c, 'type': 'fiat', 'symbol': fiat_symbols.get(c, c) } for c in fiat_codes]

    crypto_symbols = sorted({*list(_user_balances.keys()), *list(CRYPTO_IDS.keys())})
    crypto_list = [{ 'code': c, 'name': c, 'type': 'crypto' } for c in crypto_symbols]

    return jsonify(fiat_list + crypto_list)


@app.route('/api/convert', methods=['POST'])
def api_convert():
    data = request.get_json(silent=True) or {}
    from_currency = str(data.get('from_currency', '')).upper()
    to_currency = str(data.get('to_currency', '')).upper()
    amount = float(data.get('amount', 0))

    if not from_currency or not to_currency:
        return jsonify({'error': 'invalid_params'}), 400

    rate, converted = _convert_currency(from_currency, to_currency, amount)
    if rate <= 0:
        return jsonify({'error': 'conversion_failed'}), 400

    return jsonify({'rate': rate, 'converted_amount': converted, 'from': from_currency, 'to': to_currency})


@app.route('/api/balances')
def api_get_balances():
    with _user_balances_lock:
        return jsonify({'balances': _user_balances, 'status': 'success'})

@app.route('/api/balances/sync', methods=['POST'])
def api_sync_balances():
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        balances = data.get('balances', {})

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        normalized = {}
        for currency, balance in (balances or {}).items():
            code = str(currency).upper()
            if code in CRYPTO_IDS:
                try:
                    normalized[code] = float(balance)
                except Exception:
                    normalized[code] = 0.0

        with _user_balances_lock:
            template_keys = list(_user_balances.keys())
        for k in template_keys:
            normalized.setdefault(k, 0.0)

        with _synced_user_balances_lock:
            _synced_user_balances[int(user_id)] = normalized

        return jsonify({'message': 'Balances synchronized successfully', 'status': 'success'})

    except Exception as e:
        print(f"Error syncing balances: {e}")
        return jsonify({'error': 'Failed to sync balances'}), 500

@app.route('/api/balances/user/<int:user_id>')
def api_get_user_balances(user_id):
    try:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                real_balances = loop.run_until_complete(get_user_balances_from_bot_db(user_id))
                if real_balances is not None:
                    print(f"Retrieved real balances for user {user_id}: {real_balances}")
                    return jsonify({'balances': real_balances, 'user_id': user_id, 'status': 'success', 'source': 'bot_db'})
            finally:
                loop.close()
        except Exception as db_error:
            print(f"Failed to get real balances from bot DB: {db_error}")

        with _synced_user_balances_lock:
            synced = _synced_user_balances.get(int(user_id))
        if synced is not None:
            print(f"Using synced balances for user {user_id}")
            return jsonify({'balances': synced, 'user_id': user_id, 'status': 'success', 'source': 'synced'})

        with _demo_user_balances_lock:
            demo_balances = _demo_user_balances.get(int(user_id))
        if demo_balances is not None:
            print(f"Using demo balances for user {user_id}")
            return jsonify({'balances': demo_balances, 'user_id': user_id, 'status': 'success', 'source': 'demo'})

        with _user_balances_lock:
            print(f"Using zero fallback balances for user {user_id}")
            zeroed = {k: 0.0 for k in _user_balances.keys()}
            return jsonify({'balances': zeroed, 'user_id': user_id, 'status': 'success', 'source': 'fallback_zero'})
    except Exception as e:
        print(f"Error getting user balances: {e}")
        return jsonify({'error': 'Failed to get user balances'}), 500


@app.route('/api/balances/by-telegram/<int:telegram_id>')
def api_get_user_balances_by_telegram(telegram_id: int):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            internal_id = loop.run_until_complete(map_telegram_to_internal_user_id(telegram_id))
        finally:
            loop.close()
        if not internal_id:
            return jsonify({'balances': {}, 'user_id': None, 'telegram_id': telegram_id, 'status': 'success', 'source': 'not_found'}), 200
        return api_get_user_balances(internal_id)
    except Exception as e:
        print(f"Error get balances by telegram: {e}")
        return jsonify({'error': 'Failed to get balances by telegram'}), 500


@app.route('/api/user/telegram_profile', methods=['POST'])
def api_set_telegram_profile():
    try:
        data = request.get_json(silent=True) or {}
        user = data.get('user') or {}
        telegram_id = user.get('id')
        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400
        profile = {
            'id': telegram_id,
            'username': user.get('username') or '',
            'first_name': user.get('first_name') or '',
            'last_name': user.get('last_name') or '',
            'photo_url': user.get('photo_url') or user.get('photo') or ''
        }
        with _user_profiles_lock:
            _user_profiles[int(telegram_id)] = profile
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Error saving telegram profile: {e}")
        return jsonify({'error': 'Failed to save profile'}), 500


@app.route('/api/user/telegram_profile/<int:telegram_id>', methods=['GET'])
def api_get_telegram_profile(telegram_id: int):
    try:
        with _user_profiles_lock:
            profile = _user_profiles.get(int(telegram_id))
        if not profile:
            return jsonify({'ok': False, 'error': 'not_found'}), 404
        return jsonify({'ok': True, 'profile': profile})
    except Exception as e:
        print(f"Error fetching telegram profile: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500


@app.route('/api/balances/demo/set', methods=['POST'])
def api_set_demo_balances():
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        balances = data.get('balances', {})
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        normalized = {}
        for currency, balance in (balances or {}).items():
            code = str(currency).upper()
            if code in CRYPTO_IDS:
                try:
                    normalized[code] = float(balance)
                except Exception:
                    normalized[code] = 0.0
        with _user_balances_lock:
            template_keys = list(_user_balances.keys())
        for k in template_keys:
            normalized.setdefault(k, 0.0)
        with _demo_user_balances_lock:
            _demo_user_balances[int(user_id)] = normalized
        return jsonify({'ok': True, 'user_id': int(user_id)})
    except Exception as e:
        print(f"Error setting demo balances: {e}")
        return jsonify({'error': 'Failed to set demo balances'}), 500


@app.route('/api/balances/demo/reset', methods=['POST'])
def api_reset_demo_balances():
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        with _demo_user_balances_lock:
            _demo_user_balances.pop(int(user_id), None)
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Error resetting demo balances: {e}")
        return jsonify({'error': 'Failed to reset demo balances'}), 500

@app.route('/api/balances/db-status')
def api_get_db_status():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            is_connected = loop.run_until_complete(check_bot_db_connection())
            return jsonify({
                'bot_db_connected': is_connected,
                'status': 'success',
                'message': 'Bot database connection checked'
            })
        finally:
            loop.close()
    except Exception as e:
        print(f"Error checking bot DB status: {e}")
        return jsonify({
            'bot_db_connected': False,
            'status': 'error',
            'message': f'Failed to check bot database: {str(e)}'
        }), 500

@app.route('/api/balances/sync/clear/<int:user_id>', methods=['DELETE'])
def api_clear_synced_balances(user_id):
    try:
        with _synced_user_balances_lock:
            _synced_user_balances.pop(int(user_id), None)
        return jsonify({'message': f'Synced balances cleared for user {user_id}', 'status': 'success'})
    except Exception as e:
        print(f"Error clearing synced balances: {e}")
        return jsonify({'error': 'Failed to clear synced balances'}), 500


@app.route('/api/deposit', methods=['POST'])
def api_deposit():
    data = request.get_json(silent=True) or {}
    symbol = data.get('symbol', '').upper()
    amount = float(data.get('amount', 0))
    if not symbol or amount <= 0:
        return jsonify({'error': 'Invalid symbol or amount'}), 400

    with _user_balances_lock:
        _user_balances[symbol] = _user_balances.get(symbol, 0.0) + amount
        print(f"Simulated deposit: {amount} {symbol}. New balance: {_user_balances[symbol]}")
    return jsonify({'message': f'Successfully deposited {amount} {symbol}', 'status': 'success'})

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    data = request.get_json(silent=True) or {}
    symbol = data.get('symbol', '').upper()
    amount = float(data.get('amount', 0))
    address = data.get('address', '')
    network = data.get('network', '')
    if not symbol or amount <= 0 or not address:
        return jsonify({'error': 'Invalid symbol, amount, or address'}), 400

    with _user_balances_lock:
        current_balance = _user_balances.get(symbol, 0.0)
        if current_balance < amount:
            return jsonify({'error': 'Insufficient funds'}), 400
        _user_balances[symbol] = current_balance - amount
        print(f"Simulated withdrawal: {amount} {symbol} to {address}. New balance: {_user_balances[symbol]}")
    return jsonify({'message': f'Successfully withdrew {amount} {symbol}', 'status': 'success'})

@app.route('/api/swap', methods=['POST'])
def api_swap():
    data = request.get_json(silent=True) or {}
    from_symbol = data.get('from_symbol', '').upper()
    to_symbol = data.get('to_symbol', '').upper()
    from_amount = float(data.get('from_amount', 0))

    if not from_symbol or not to_symbol or from_amount <= 0:
        return jsonify({'error': 'Invalid symbols or amount'}), 400

    if from_symbol == to_symbol:
        return jsonify({'error': 'Cannot swap to the same currency'}), 400

    crypto_prices_usd = _cached_fetch('crypto_prices', _fetch_crypto_prices_usd)

    from_price_usd = crypto_prices_usd.get(from_symbol, 0)
    to_price_usd = crypto_prices_usd.get(to_symbol, 0)

    if from_price_usd == 0 or to_price_usd == 0:
        return jsonify({'error': 'Could not get live prices for swap currencies'}), 400

    usd_value = from_amount * from_price_usd
    to_amount = usd_value / to_price_usd

    with _user_balances_lock:
        current_from_balance = _user_balances.get(from_symbol, 0.0)
        if current_from_balance < from_amount:
            return jsonify({'error': 'Insufficient funds for swap'}), 400

        _user_balances[from_symbol] = current_from_balance - from_amount
        _user_balances[to_symbol] = _user_balances.get(to_symbol, 0.0) + to_amount

        print(f"Simulated swap: {from_amount} {from_symbol} to {to_amount:.4f} {to_symbol}. "
              f"New balances: {from_symbol}={_user_balances[from_symbol]}, {to_symbol}={_user_balances[to_symbol]}")

    return jsonify({
        'message': f'Successfully swapped {from_amount} {from_symbol} for {to_amount:.4f} {to_symbol}',
        'from_new_balance': _user_balances[from_symbol],
        'to_new_balance': _user_balances[to_symbol],
        'to_amount_received': to_amount,
        'status': 'success'
    })


@app.route('/api/swap_rate', methods=['POST'])
def api_swap_rate():
    data = request.get_json(silent=True) or {}
    from_symbol = data.get('from_symbol', '').upper()
    to_symbol = data.get('to_symbol', '').upper()

    if not from_symbol or not to_symbol:
        return jsonify({'error': 'Invalid symbols'}), 400

    crypto_prices_usd = _cached_fetch('crypto_prices', _fetch_crypto_prices_usd)

    from_price_usd = crypto_prices_usd.get(from_symbol, 0)
    to_price_usd = crypto_prices_usd.get(to_symbol, 0)

    if from_price_usd == 0 or to_price_usd == 0:
        return jsonify({'error': 'Could not get live prices for swap currencies'}), 400

    rate = from_price_usd / to_price_usd
    return jsonify({'rate': rate, 'status': 'success'})


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    with _cache_lock:
        base = _cache['user_settings']['data']['base_currency']
    return jsonify({'base_currency': base})


@app.route('/api/settings/currency', methods=['POST'])
def api_set_currency():
    data = request.get_json(silent=True) or {}
    code = str(data.get('code', 'USD')).upper()
    if not code.isalpha() or len(code) not in (2, 3):
        return jsonify({'error': 'invalid_code'}), 400
    with _cache_lock:
        _cache['user_settings']['data']['base_currency'] = code
    return jsonify({'ok': True, 'base_currency': code})


@app.route('/api/bot/status')
def bot_status():
    return {
        'status': 'online',
        'users': 150,
        'transactions': 2500
    }

def _start_ngrok(port: int = 5000) -> str:
    try:
        auth = os.environ.get('NGROK_AUTHTOKEN')
        if auth:
            subprocess.run(['ngrok', 'config', 'add-authtoken', auth], check=False)
        proc = subprocess.Popen(['ngrok', 'http', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time as _t
        import requests as _rq
        for _ in range(30):
            _t.sleep(1)
            try:
                r = _rq.get('http://127.0.0.1:4040/api/tunnels', timeout=1)
                data = r.json()
                for t in data.get('tunnels', []):
                    if t.get('proto') == 'https':
                        return t.get('public_url')
            except Exception:
                continue
        return ''
    except Exception:
        return ''


def _start_bot() -> subprocess.Popen:
    env = os.environ.copy()
    cwd = os.path.join(os.getcwd(), 'BOT')
    return subprocess.Popen([sys.executable, '-m', 'app.bot.main'], cwd=cwd)


def get_db_connection():
    db_path = "cryptobot.db"
    if not os.path.exists(db_path):
        db_path = "BOT/cryptobot.db"
    return sqlite3.connect(db_path)

def init_verification_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_verification (
                user_id TEXT PRIMARY KEY,
                phone_verified BOOLEAN DEFAULT FALSE,
                phone_number TEXT,
                documents_uploaded BOOLEAN DEFAULT FALSE,
                documents_verification_pending BOOLEAN DEFAULT FALSE,
                front_document TEXT,
                back_document TEXT,
                address_verified BOOLEAN DEFAULT FALSE,
                country TEXT,
                city TEXT,
                address TEXT,
                postal_code TEXT,
                video_verified BOOLEAN DEFAULT FALSE,
                video_verification_pending BOOLEAN DEFAULT FALSE,
                video_file TEXT,
                verification_complete BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error initializing verification table: {e}")
        return False

def update_user_settings(user_id, setting_type, value):
    try:
        conn = sqlite3.connect('cryptobot.db', timeout=10.0)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                timezone VARCHAR(50) NOT NULL,
                local_currency VARCHAR(10) NOT NULL,
                bot_language VARCHAR(10) NOT NULL,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                updated_at DATETIME,
                PRIMARY KEY (id),
                UNIQUE(user_id)
            )
        ''')

        user_id_int = int(user_id) if user_id else 1

        if setting_type == 'timezone':
            cursor.execute('SELECT id FROM user_settings WHERE user_id = ?', (user_id_int,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE user_settings SET timezone = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (value, user_id_int))
            else:
                cursor.execute('''
                    INSERT INTO user_settings (user_id, timezone, local_currency, bot_language, updated_at)
                    VALUES (?, ?, 'USD', 'ru', CURRENT_TIMESTAMP)
                ''', (user_id_int, value))
        elif setting_type == 'language':
            cursor.execute('SELECT id FROM user_settings WHERE user_id = ?', (user_id_int,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE user_settings SET bot_language = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (value, user_id_int))
            else:
                cursor.execute('''
                    INSERT INTO user_settings (user_id, timezone, local_currency, bot_language, updated_at)
                    VALUES (?, 'UTC', 'USD', ?, CURRENT_TIMESTAMP)
                ''', (user_id_int, value))
        elif setting_type == 'currency':
            cursor.execute('SELECT id FROM user_settings WHERE user_id = ?', (user_id_int,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE user_settings SET local_currency = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (value, user_id_int))
            else:
                cursor.execute('''
                    INSERT INTO user_settings (user_id, timezone, local_currency, bot_language, updated_at)
                    VALUES (?, 'UTC', ?, 'ru', CURRENT_TIMESTAMP)
                ''', (user_id_int, value))
        elif setting_type == 'sounds_enabled':
            pass

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"Error updating user settings: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def update_user_verification_status(user_id, status, data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        init_verification_table()

        cursor.execute('SELECT user_id FROM user_verification WHERE user_id = ?', (user_id,))
        user_exists = cursor.fetchone()

        if status == 'phone_verified':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET phone_verified = TRUE, phone_number = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (data.get('phone_number', ''), user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, phone_verified, phone_number)
                    VALUES (?, TRUE, ?)
                ''', (user_id, data.get('phone_number', '')))
        elif status == 'phone_verification_pending':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET phone_verification_pending = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, phone_verification_pending)
                    VALUES (?, TRUE)
                ''', (user_id,))

        elif status == 'documents_uploaded':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET documents_uploaded = TRUE, front_document = ?, back_document = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (data.get('front_document', ''), data.get('back_document', ''), user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, documents_uploaded, front_document, back_document)
                    VALUES (?, TRUE, ?, ?)
                ''', (user_id, data.get('front_document', ''), data.get('back_document', '')))
        elif status == 'documents_verified':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET documents_verified = TRUE, documents_verification_pending = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, documents_verified)
                    VALUES (?, TRUE)
                ''', (user_id,))

        elif status == 'address_verified':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET address_verified = TRUE, country = ?, city = ?, address = ?, postal_code = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (data.get('country', ''), data.get('city', ''), data.get('address', ''), data.get('postal_code', ''), user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, address_verified, country, city, address, postal_code)
                    VALUES (?, TRUE, ?, ?, ?, ?)
                ''', (user_id, data.get('country', ''), data.get('city', ''), data.get('address', ''), data.get('postal_code', '')))
        elif status == 'address_verification_pending':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET address_verification_pending = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, address_verification_pending)
                    VALUES (?, TRUE)
                ''', (user_id,))

        elif status == 'video_verified':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET video_verified = TRUE, video_file = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (data.get('video_file', ''), user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, video_verified, video_file)
                    VALUES (?, TRUE, ?)
                ''', (user_id, data.get('video_file', '')))

        elif status == 'documents_verification_pending':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET documents_verification_pending = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, documents_verification_pending)
                    VALUES (?, TRUE)
                ''', (user_id,))

        elif status == 'video_verification_pending':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET video_verification_pending = TRUE, video_file = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (data.get('video_file', ''), user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, video_verification_pending, video_file)
                    VALUES (?, TRUE, ?)
                ''', (user_id, data.get('video_file', '')))
        elif status == 'verification_rejected':
            if user_exists:
                cursor.execute('''
                    UPDATE user_verification
                    SET verification_rejected = TRUE, rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (data.get('rejection_reason', ''), user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_verification (user_id, verification_rejected, rejection_reason)
                    VALUES (?, TRUE, ?)
                ''', (user_id, data.get('rejection_reason', '')))

        cursor.execute('''
            SELECT phone_verified, documents_uploaded, address_verified, video_verified
            FROM user_verification WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()

        if result and all(result):
            cursor.execute('''
                UPDATE user_verification
                SET verification_complete = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"Error updating verification status: {e}")
        return False

def get_user_verification_status(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                phone_verified,
                phone_verification_pending,
                phone_number,
                documents_uploaded,
                documents_verified,
                documents_verification_pending,
                front_document,
                back_document,
                address_verified,
                address_verification_pending,
                country,
                city,
                address,
                postal_code,
                video_verified,
                video_verification_pending,
                video_file,
                verification_rejected,
                rejection_reason,
                verification_complete
            FROM user_verification WHERE user_id = ?
        ''', (user_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'phone_verified': bool(result[0]),
                'phone_verification_pending': bool(result[1]),
                'phone_number': result[2],
                'documents_uploaded': bool(result[3]),
                'documents_verified': bool(result[4]),
                'documents_verification_pending': bool(result[5]),
                'front_document': result[6],
                'back_document': result[7],
                'address_verified': bool(result[8]),
                'address_verification_pending': bool(result[9]),
                'country': result[10],
                'city': result[11],
                'address': result[12],
                'postal_code': result[13],
                'video_verified': bool(result[14]),
                'video_verification_pending': bool(result[15]),
                'video_file': result[16],
                'verification_rejected': bool(result[17]),
                'rejection_reason': result[18],
                'verification_complete': bool(result[19])
            }
        else:
            return {
                'phone_verified': False,
                'phone_verification_pending': False,
                'phone_number': '',
                'documents_uploaded': False,
                'documents_verified': False,
                'documents_verification_pending': False,
                'front_document': '',
                'back_document': '',
                'address_verified': False,
                'address_verification_pending': False,
                'country': '',
                'city': '',
                'address': '',
                'postal_code': '',
                'video_verified': False,
                'video_verification_pending': False,
                'video_file': '',
                'verification_rejected': False,
                'rejection_reason': '',
                'verification_complete': False
            }

    except Exception as e:
        print(f"Error getting verification status: {e}")
        return {
            'phone_verified': False,
            'phone_verification_pending': False,
            'phone_number': '',
            'documents_uploaded': False,
            'documents_verified': False,
            'documents_verification_pending': False,
            'front_document': '',
            'back_document': '',
            'address_verified': False,
            'address_verification_pending': False,
            'country': '',
            'city': '',
            'address': '',
            'postal_code': '',
            'video_verified': False,
            'video_verification_pending': False,
            'video_file': '',
            'verification_rejected': False,
            'rejection_reason': '',
            'verification_complete': False
        }

if __name__ == '__main__':
    try:
        load_dotenv()
    except Exception:
        pass
    directories = ['static/css', 'static/js', 'static/images', 'static/icons', 'static/cursors', 'templates']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    light_start = os.environ.get('LIGHT_START') == '1'
    if light_start:
        print('LIGHT_START=1 → skipping ngrok and bot startup for faster boot')
        bot_proc = None
    else:
        print('Starting ngrok tunnel...')
        public_url = _start_ngrok(5000)
        if public_url:
            os.environ['NGROK_URL'] = public_url
            os.environ['WEBAPP_URL'] = public_url
            print(f'ngrok tunnel: {public_url}')
        else:
            print('ngrok not started or URL not found; proceeding without it.')

        print('Starting Telegram bot...')
        bot_proc = _start_bot()

    print("Flask application starting...")
    print("Available routes:")
    print("- / - Main page")
    print("- /deposit - Deposit page")
    print("- /withdraw - Withdraw page")
    print("- /swap - Swap page")
    print("- /settings - Settings page")
    print("- /timezones - Timezones page")
    print("- /language - Language page")
    print("- /address_book - Address Book page")
    print("- /security - Security page")
    print("- /update_info - Update Info page")
    print("- /currency_selection - Currency Selection page")
    print("- /user_menu - User Menu page")
    print("- /p2p_merchant - P2P Merchant page")
    print("- /p2c_merchant - P2C Merchant page")
    print("- /verification - Verification page")
    print("- /privacy_policy - Privacy Policy page")
    print("- /aml_policy - AML Policy page")
    print("- /css/<filename> - CSS files")
    print("- /js/<filename> - JavaScript files")
    print("- /images/<filename> - Image files")
    print("- /icons/<filename> - Icon files")
    print("- /cursors/<filename> - Cursor files")
    print("- /api/crypto/prices - Crypto prices API")
    print("- /api/bot/status - Bot status API")

    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False, threaded=True)
    finally:
        if not light_start and bot_proc and bot_proc.poll() is None:
            bot_proc.terminate()

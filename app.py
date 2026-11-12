"""FareScout: dependency-free personal travel dashboard and JSON API."""
import json, os, sqlite3, secrets, argparse
from exchange import get_rates, ExchangeError
from providers import status as provider_status, search as search_flights, validate_search, ProviderError
from datetime import datetime, timezone, date
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
DB = os.getenv('FARESCOUT_DB', str(ROOT / 'farescout.db'))
AIRPORTS = {'YHZ': 'Halifax', 'YYZ': 'Toronto', 'YUL': 'Montreal', 'HRE': 'Harare'}
def now(): return datetime.now(timezone.utc).isoformat()
def connect():
    db = sqlite3.connect(DB); db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON'); return db

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS watches(id TEXT PRIMARY KEY, origin TEXT NOT NULL, destination TEXT NOT NULL, departure TEXT NOT NULL, return_date TEXT NOT NULL, budget REAL NOT NULL, currency TEXT NOT NULL, adults INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS prices(id INTEGER PRIMARY KEY, watch_id TEXT REFERENCES watches(id) ON DELETE CASCADE, amount REAL NOT NULL, currency TEXT NOT NULL, source TEXT NOT NULL, observed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, watch_id TEXT REFERENCES watches(id) ON DELETE CASCADE, message TEXT NOT NULL, created_at TEXT NOT NULL, emailed INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS saved(deal_id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS search_usage(id INTEGER PRIMARY KEY, requested_at TEXT NOT NULL);
        ''')

def validate_watch(data):
    origin = str(data.get('origin', '')).upper()
    destination = str(data.get('destination', '')).strip()
    if origin not in AIRPORTS: raise ValueError('Choose a supported departure airport.')
    if not 2 <= len(destination) <= 80: raise ValueError('Enter a destination between 2 and 80 characters.')
    try:
        start, end = date.fromisoformat(data['departure']), date.fromisoformat(data['return_date'])
        budget, adults = float(data['budget']), int(data.get('adults', 1))
    except (KeyError, ValueError, TypeError): raise ValueError('Enter valid dates, budget and travellers.')
    if start < date.today() or end < start: raise ValueError('Choose future dates with return after departure.')
    if not 0 < budget <= 1000000 or not 1 <= adults <= 9: raise ValueError('Budget or traveller count is outside the supported range.')
    currency = data.get('currency', 'CAD')
    if currency not in ('CAD', 'USD'): raise ValueError('Choose CAD or USD.')
    return (secrets.token_hex(8), origin, destination, start.isoformat(), end.isoformat(), budget, currency, adults, now())

def record_price(watch_id, amount, currency, source):
    """Called by a trusted provider adapter only; no fabricated historical observations."""
    if not isinstance(amount, (int, float)) or not 0 < amount < 10000000: raise ValueError('Invalid price')
    with connect() as db:
        watch = db.execute('SELECT * FROM watches WHERE id=?', (watch_id,)).fetchone()
        if not watch or currency != watch['currency']: raise ValueError('Watch or currency mismatch')
        previous = db.execute('SELECT amount FROM prices WHERE watch_id=? ORDER BY id DESC LIMIT 1', (watch_id,)).fetchone()
        db.execute('INSERT INTO prices(watch_id,amount,currency,source,observed_at) VALUES(?,?,?,?,?)', (watch_id, amount, currency, source, now()))
        if amount <= watch['budget'] and (previous is None or amount < previous['amount']):
            db.execute('INSERT INTO notifications(watch_id,message,created_at) VALUES(?,?,?)', (watch_id, f"{watch['destination']} is within your budget: {currency} {amount:,.2f} for {watch['adults']} traveller(s). Source: {source}", now()))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)
    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        self.send_header('Referrer-Policy', 'no-referrer'); super().end_headers()
    def send_json(self, data, status=200):
        body = json.dumps(data).encode(); self.send_response(status)
        self.send_header('Content-Type', 'application/json'); self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/config': return self.send_json({'airports': AIRPORTS, 'mode': 'demo', 'live_tracking': False})
        if path == '/api/exchange':
            try: return self.send_json(get_rates())
            except ExchangeError as error: return self.send_json({'error':str(error)},503)
        if path == '/api/provider': return self.send_json(provider_status())
        if path == '/api/deals': return self.send_json(json.loads((ROOT / 'data.json').read_text()))
        if path == '/api/watches':
            with connect() as db:
                watches = [dict(x) for x in db.execute('SELECT * FROM watches ORDER BY created_at DESC')]
                for w in watches: w['history'] = [dict(x) for x in db.execute('SELECT amount,currency,source,observed_at FROM prices WHERE watch_id=? ORDER BY id', (w['id'],))]
            return self.send_json(watches)
        if path == '/api/saved':
            with connect() as db: return self.send_json([x[0] for x in db.execute('SELECT deal_id FROM saved')])
        if path == '/api/notifications':
            with connect() as db: return self.send_json([dict(x) for x in db.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 100')])
        if path.startswith('/api/'): return self.send_json({'error':'Not found'},404)
        return super().do_GET()
    def do_POST(self):
        # Reject cross-origin writes; this dashboard is intended for a single trusted user.
        if self.headers.get('Sec-Fetch-Site') == 'cross-site': return self.send_json({'error':'Cross-origin write rejected'},403)
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'): return self.send_json({'error':'Origin mismatch'},403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192: raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict): raise ValueError('Expected a JSON object')
            path = urlparse(self.path).path
            if path == '/api/flights/search':
                validate_search(data)
                if not provider_status()['search_enabled']:
                    return self.send_json({'error':'Flight search is not connected or live use is disabled. Configure the server with a Duffel test token first.'},503)
                with connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    count = db.execute('SELECT COUNT(*) FROM search_usage WHERE substr(requested_at,1,10)=?',(now()[:10],)).fetchone()[0]
                    limit = max(1,min(1000,int(os.getenv('DUFFEL_DAILY_SEARCH_LIMIT','20'))))
                    if count >= limit: return self.send_json({'error':'Daily search limit reached. No further provider requests will be made today.'},429)
                    db.execute('INSERT INTO search_usage(requested_at) VALUES(?)',(now(),))
                try: return self.send_json(search_flights(data))
                except ProviderError as error: return self.send_json({'error':str(error)},502)
            with connect() as db:
                if path == '/api/watches':
                    values = validate_watch(data)
                    db.execute('INSERT INTO watches VALUES(?,?,?,?,?,?,?,?,?)', values)
                    return self.send_json({'id':values[0]},201)
                if path == '/api/watches/delete':
                    db.execute('DELETE FROM watches WHERE id=?', (str(data.get('id','')),)); return self.send_json({'ok':True})
                if path == '/api/saved':
                    deal_id = str(data.get('id',''))
                    ids = {x['id'] for x in json.loads((ROOT / 'data.json').read_text())['deals']}
                    if deal_id not in ids: raise ValueError('Unknown deal')
                    if data.get('saved'): db.execute('INSERT OR IGNORE INTO saved VALUES(?)',(deal_id,))
                    else: db.execute('DELETE FROM saved WHERE deal_id=?',(deal_id,))
                    return self.send_json({'ok':True})
            return self.send_json({'error':'Not found'},404)
        except (ValueError, TypeError, json.JSONDecodeError) as error: return self.send_json({'error':str(error)},400)
    def log_message(self, fmt, *args): pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--host', default='127.0.0.1'); parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--strictPort', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(); init_db()
    print(f'FareScout running at http://{args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host,args.port), Handler).serve_forever()

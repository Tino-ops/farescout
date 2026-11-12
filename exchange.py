"""Daily indicative FX rates from Bank of Canada; no invented fallback rates."""
import json, math, threading, time
from datetime import date, datetime, timezone
from urllib.request import Request, urlopen

URL='https://www.bankofcanada.ca/valet/observations/group/FX_RATES_DAILY/json?recent=7'
_lock=threading.Lock()
_cache=None
_fetched=0

class ExchangeError(Exception): pass

def normalize(payload):
    rates={'CAD':{'cad_per_unit':1.0,'date':None}}
    today=date.today()
    for observation in sorted(payload.get('observations',[]),key=lambda x:x.get('d','')):
        try: day=date.fromisoformat(observation['d'])
        except (ValueError,KeyError,TypeError): continue
        if not 0 <= (today-day).days <= 7: continue
        for series,value in observation.items():
            if not (series.startswith('FX') and series.endswith('CAD') and len(series)==8):continue
            try: rate=float(value['v'])
            except (ValueError,KeyError,TypeError):continue
            if math.isfinite(rate) and rate>0:
                rates[series[2:5]]={'cad_per_unit':rate,'date':day.isoformat()}
    if 'USD' not in rates:raise ExchangeError('No recent valid USD/CAD rate available.')
    return {'source':'Bank of Canada','source_url':'https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/','rates':rates,'retrieved_at':datetime.now(timezone.utc).isoformat(),'indicative':True,'note':'Derived currency estimates using daily indicative rates, available free from the Bank of Canada. Card, bank and booking-provider rates and fees may differ.'}

def get_rates():
    global _cache,_fetched
    with _lock:
        # Both successful results and failures are cached to avoid repeated outbound calls.
        if _fetched and time.monotonic()-_fetched<3600:
            if _cache:return _cache
            raise ExchangeError('Exchange rates temporarily unavailable. Original prices are shown.')
        try:
            request=Request(URL,headers={'Accept':'application/json','User-Agent':'FareScout/0.1'})
            with urlopen(request,timeout=8) as response:
                raw=response.read(1_000_001)
            if len(raw)>1_000_000:raise ExchangeError('Unexpected exchange-rate response.')
            _cache=normalize(json.loads(raw));_fetched=time.monotonic();return _cache
        except Exception:
            _fetched=time.monotonic()
            # A failed refresh never silently reuses an outdated rate.
            _cache=None
            raise ExchangeError('Exchange rates temporarily unavailable. Original prices are shown.') from None

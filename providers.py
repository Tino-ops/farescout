"""Duffel v2 on-demand flight search. Secrets stay on the server."""
import json, os, re, math
from datetime import date, datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class ProviderError(Exception): pass

def status():
    token = os.getenv('DUFFEL_ACCESS_TOKEN', '')
    enabled = bool(token)
    live = token.startswith('duffel_live_')
    allowed = not live or os.getenv('DUFFEL_ALLOW_LIVE') == '1'
    return {'provider':'Duffel', 'configured':enabled, 'mode':'live' if live else 'test' if enabled else 'disconnected', 'search_enabled':enabled and allowed, 'scheduled_monitoring':False}

def validate_search(data):
    origin, destination = str(data.get('origin','')).upper(), str(data.get('destination','')).upper()
    if origin not in ('YHZ','YYZ','YUL','HRE') or not re.fullmatch('[A-Z]{3}', destination) or origin == destination:
        raise ValueError('Choose a supported departure and a different three-letter destination airport code, such as CPT or LHR.')
    try:
        start, end = date.fromisoformat(data['departure']), date.fromisoformat(data['return_date'])
        adults = int(data.get('adults',1))
    except (KeyError,ValueError,TypeError): raise ValueError('Enter valid departure and return dates and adults.')
    if start < date.today() or end < start or not 1 <= adults <= 9: raise ValueError('Choose future dates and 1–9 adults.')
    return {'origin':origin,'destination':destination,'departure':start.isoformat(),'return_date':end.isoformat(),'adults':adults}

def normalize(payload):
    result = payload.get('data',{})
    # Missing live_mode must never turn sandbox data into live offers.
    live = result.get('live_mode') is True
    checked = datetime.now(timezone.utc).isoformat()
    rows=[]
    for offer in result.get('offers',[]):
        try:
            amount=float(offer['total_amount']); currency=offer['total_currency']
            expires=datetime.fromisoformat(offer['expires_at'].replace('Z','+00:00'))
            if not math.isfinite(amount) or amount <= 0 or not re.fullmatch('[A-Z]{3}',currency) or expires <= datetime.now(timezone.utc): continue
            segments=[]
            for part in offer['slices']:
                for seg in part['segments']:
                    segments.append({'origin':seg['origin']['iata_code'],'destination':seg['destination']['iata_code'],'departure':seg['departing_at'],'arrival':seg['arriving_at'],'operating_carrier':seg['operating_carrier']['name'],'flight_number':seg.get('operating_carrier_flight_number',''),'passenger_fares':[{'cabin':p.get('cabin_class'),'fare':p.get('fare_basis_code'),'baggage':p.get('baggages',[])} for p in seg.get('passengers',[])]})
            rows.append({'id':offer['id'],'amount':amount,'currency':currency,'live':live,'source':'Duffel','checked_at':checked,'expires_at':offer['expires_at'],'airline':offer['owner']['name'],'segments':segments,'conditions':offer.get('conditions',{}),'total_passengers':len(offer.get('passengers',[])),'tax_amount':offer.get('tax_amount'),'tax_currency':offer.get('tax_currency')})
        except (KeyError,ValueError,TypeError): continue
    # Keep currencies separate: no fabricated cross-currency ranking or conversion.
    return {'provider':'Duffel','mode':'live' if live else 'test','checked_at':checked,'offers':sorted(rows,key=lambda o:(o['currency'],o['amount']))[:30], 'note':'User-triggered quote, not a verified sale or observed price drop. Availability must be rechecked before booking.'}

def search(data, transport=None):
    query=validate_search(data); config=status()
    if not config['configured']: raise ProviderError('Duffel is not connected. Configure DUFFEL_ACCESS_TOKEN on the server using a test token first.')
    if not config['search_enabled']: raise ProviderError('Live searches are disabled. Review Duffel fees and set DUFFEL_ALLOW_LIVE=1 on the server to enable them.')
    body={'data':{'slices':[{'origin':query['origin'],'destination':query['destination'],'departure_date':query['departure']},{'origin':query['destination'],'destination':query['origin'],'departure_date':query['return_date']}], 'passengers':[{'type':'adult'} for _ in range(query['adults'])], 'cabin_class':'economy','max_connections':2}}
    request=Request('https://api.duffel.com/air/offer_requests?return_offers=true&supplier_timeout=15000',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+os.environ['DUFFEL_ACCESS_TOKEN'],'Duffel-Version':'v2','Content-Type':'application/json','Accept':'application/json'},method='POST')
    try:
        with (transport or urlopen)(request,timeout=25) as response:
            raw=response.read(5_000_001)
            if len(raw)>5_000_000: raise ProviderError('Provider response exceeded the supported size.')
            payload=json.loads(raw)
        if not isinstance(payload,dict) or not isinstance(payload.get('data'),dict): raise ProviderError('Unexpected provider response.')
        return normalize(payload)
    except HTTPError as error:
        code=error.code
        raise ProviderError('Provider authentication failed; check your server token.' if code in (401,403) else 'Provider rate limit reached. Try later.' if code==429 else 'Flight provider rejected the search. Check the route, dates and account status.') from None
    except (URLError,TimeoutError,json.JSONDecodeError,OSError): raise ProviderError('Flight provider is unavailable or timed out. Try again later.') from None

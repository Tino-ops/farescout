import unittest,os,json
from unittest.mock import patch
from datetime import date,timedelta,datetime,timezone
import providers
class ProviderTests(unittest.TestCase):
    def query(self):return dict(origin='HRE',destination='CPT',departure=str(date.today()+timedelta(days=30)),return_date=str(date.today()+timedelta(days=35)),adults=2)
    def fixture(self,live=False):return {'data':{'live_mode':live,'offers':[{'id':'off_test','total_amount':'499.50','total_currency':'USD','expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'owner':{'name':'Fixture airline'},'passengers':[{},{}],'slices':[{'segments':[{'origin':{'iata_code':'HRE'},'destination':{'iata_code':'CPT'},'departing_at':'2027-01-01T09:00:00','arriving_at':'2027-01-01T12:00:00','operating_carrier':{'name':'Fixture operator'},'passengers':[]}]}]}]}}
    def test_missing_key_and_live_gate(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(providers.status()['search_enabled'])
            with self.assertRaises(providers.ProviderError):providers.search(self.query())
        with patch.dict(os.environ,{'DUFFEL_ACCESS_TOKEN':'duffel_live_fixture'},clear=True):
            with self.assertRaises(providers.ProviderError):providers.search(self.query())
    def test_test_mode_not_live_and_total_not_multiplied(self):
        r=providers.normalize(self.fixture());self.assertEqual(r['mode'],'test');self.assertFalse(r['offers'][0]['live']);self.assertEqual(r['offers'][0]['amount'],499.5);self.assertEqual(r['offers'][0]['segments'][0]['operating_carrier'],'Fixture operator')
    def test_missing_mode_defaults_test_and_expired_dropped(self):
        p=self.fixture();del p['data']['live_mode'];self.assertEqual(providers.normalize(p)['mode'],'test')
        p['data']['offers'][0]['expires_at']='2020-01-01T00:00:00+00:00';self.assertEqual(providers.normalize(p)['offers'],[])
    def test_airport_validation(self):
        q=self.query();q['destination']='Cape Town'
        with self.assertRaises(ValueError):providers.validate_search(q)
    def test_transport_roundtrip_payload_and_secret_not_returned(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps(ProviderTests().fixture()).encode()
        def transport(req,timeout):
            self.assertEqual(req.full_url.split('?')[0],'https://api.duffel.com/air/offer_requests')
            data=json.loads(req.data)['data'];self.assertEqual(len(data['slices']),2);self.assertEqual(data['slices'][1]['origin'],'CPT');self.assertEqual(len(data['passengers']),2);return Response()
        with patch.dict(os.environ,{'DUFFEL_ACCESS_TOKEN':'duffel_test_fixture'},clear=True):
            result=providers.search(self.query(),transport=transport);self.assertNotIn('duffel_test_fixture',json.dumps(result))

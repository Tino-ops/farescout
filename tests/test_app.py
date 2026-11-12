import unittest, tempfile, threading, json, urllib.request, urllib.error
from datetime import date,timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
import app

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();app.DB=str(Path(self.tmp.name)/'test.db');app.init_db()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self): self.server.shutdown();self.server.server_close();self.tmp.cleanup()
    def request(self,path,data=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin: headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5) as response: return json.load(response)
    def watch(self,**changes):
        data=dict(origin='HRE',destination='Cape Town',departure=str(date.today()+timedelta(days=30)),return_date=str(date.today()+timedelta(days=35)),budget=500,currency='USD',adults=1);data.update(changes)
        return self.request('/api/watches',data)['id']
    def test_persist_harare_watch_and_delete(self):
        id=self.watch();w=self.request('/api/watches')[0];self.assertEqual(w['origin'],'HRE');self.assertEqual(w['history'],[])
        self.request('/api/watches/delete',{'id':id});self.assertEqual(self.request('/api/watches'),[])
    def test_reject_invalid_budget_date_and_airport(self):
        for change in ({'budget':-1},{'departure':'2020-01-01'},{'origin':'XXX'},{'adults':10}):
            with self.assertRaises(urllib.error.HTTPError) as error:self.watch(**change)
            self.assertEqual(error.exception.code,400)
    def test_price_threshold_and_no_duplicate_alerts(self):
        id=self.watch()
        for amount in (600,490,490,480):app.record_price(id,amount,'USD','Test provider')
        self.assertEqual(len(self.request('/api/notifications')),2)
        self.assertEqual(len(self.request('/api/watches')[0]['history']),4)
        with self.assertRaises(ValueError):app.record_price(id,450,'CAD','Test provider')
    def test_saved_idempotence(self):
        for _ in range(2):self.request('/api/saved',{'id':'lisbon','saved':True})
        self.assertEqual(self.request('/api/saved'),['lisbon'])
        self.request('/api/saved',{'id':'lisbon','saved':False});self.assertEqual(self.request('/api/saved'),[])
    def test_cross_origin_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/saved',{'id':'lisbon','saved':True},origin='https://example.com')
        self.assertEqual(error.exception.code,403)
    def test_provider_disconnected_and_no_secret(self):
        from unittest.mock import patch
        import os
        with patch.dict(os.environ, {}, clear=True):
            result=self.request('/api/provider');self.assertFalse(result['search_enabled'])
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/flights/search',dict(origin='HRE',destination='CPT',departure=str(date.today()+timedelta(days=30)),return_date=str(date.today()+timedelta(days=35)),adults=1))
            self.assertEqual(error.exception.code,503)
    def test_provider_quota_blocks_second_request(self):
        from unittest.mock import patch
        import os
        query=dict(origin='HRE',destination='CPT',departure=str(date.today()+timedelta(days=30)),return_date=str(date.today()+timedelta(days=35)),adults=1)
        with patch.dict(os.environ, {'DUFFEL_ACCESS_TOKEN':'duffel_test_fixture','DUFFEL_DAILY_SEARCH_LIMIT':'1'}, clear=True), patch('app.search_flights',return_value={'offers':[]}) as mock:
            self.request('/api/flights/search',query)
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/flights/search',query)
            self.assertEqual(error.exception.code,429);self.assertEqual(mock.call_count,1)
    def test_demo_data_is_explicit(self):
        data=self.request('/api/deals')['deals'];self.assertTrue(all(d['demo'] and d['checked_at'] is None for d in data))
        self.assertEqual({d['origin'] for d in data},{'YHZ','YYZ','YUL','HRE'})

if __name__=='__main__':unittest.main()

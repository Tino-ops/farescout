import unittest
from datetime import date,timedelta
from unittest.mock import patch
import exchange
class ExchangeTests(unittest.TestCase):
    def payload(self,rate='1.4',age=0):return {'observations':[{'d':str(date.today()-timedelta(days=age)),'FXUSDCAD':{'v':rate},'FXGBPCAD':{'v':'1.9'}}]}
    def test_parse_rates_and_source(self):
        result=exchange.normalize(self.payload());self.assertEqual(result['rates']['CAD']['cad_per_unit'],1);self.assertEqual(result['rates']['USD']['cad_per_unit'],1.4);self.assertEqual(result['source'],'Bank of Canada')
    def test_reject_invalid_stale_future(self):
        for payload in (self.payload('NaN'),self.payload('-1'),self.payload(age=9),self.payload(age=-1)):
            with self.assertRaises(exchange.ExchangeError):exchange.normalize(payload)
    def test_failed_refresh_does_not_return_old_cache(self):
        with patch.object(exchange,'_fetched',0),patch.object(exchange,'_cache',{'old':True}),patch('exchange.urlopen',side_effect=OSError('offline')):
            with self.assertRaises(exchange.ExchangeError):exchange.get_rates()
            self.assertIsNone(exchange._cache)

"""Run from cron after adding a licensed provider adapter. No automatic bookings."""
import os, smtplib, ssl
from email.message import EmailMessage
from app import connect, init_db, record_price

def collect(provider):
    """Provider.search(watch) returns matching TOTAL quotes or None.
    An adapter must preserve dates, travellers, baggage/fare or room conditions,
    currency and taxes. Validate provider storage/monitoring terms first.
    """
    with connect() as db: watches = [dict(x) for x in db.execute('SELECT * FROM watches')]
    for watch in watches:
        quote = provider.search(watch)
        if quote: record_price(watch['id'], quote['amount'], quote['currency'], quote['source'])

def send_alerts():
    required = ['SMTP_HOST','SMTP_USER','SMTP_PASSWORD','ALERT_TO','ALERT_FROM']
    if not all(os.getenv(x) for x in required):
        print('Email disabled: configure SMTP settings in the environment.'); return
    with connect() as db: rows = db.execute('SELECT * FROM notifications WHERE emailed=0').fetchall()
    if not rows: return
    with smtplib.SMTP_SSL(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT','465')), context=ssl.create_default_context()) as smtp:
        smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
        for row in rows:
            msg = EmailMessage(); msg['Subject'] = 'FareScout price alert'; msg['From'] = os.environ['ALERT_FROM']; msg['To'] = os.environ['ALERT_TO']; msg.set_content(row['message'])
            smtp.send_message(msg)
            with connect() as db: db.execute('UPDATE notifications SET emailed=1 WHERE id=?',(row['id'],))
if __name__ == '__main__':
    init_db(); send_alerts()

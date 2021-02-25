import re
import smtplib
import json
import urllib.request as request
import socketio
from bs4 import BeautifulSoup
from email.message import EmailMessage

# Forms types to search through
RELEVANT_FORMS = {'10-K', '10-Q', '8-K'}

'''
Check if a filing mentions the word "Bitcoin"

Arguments:
    url - URL to an SEC filing
'''
def mentions_bitcoin(url):
    fp = request.urlopen(url)
    fp_bytes = fp.read()

    html_doc = fp_bytes.decode('utf8')
    soup = BeautifulSoup(html_doc, 'html.parser')

    p_elements = soup.find_all('p')

    for element in p_elements:
        if element.find(text=re.compile('[bB]itcoin')):
            # Found a mention of bitcoin
            fp.close()
            return True

    fp.close()
    return False

'''
Send an email as an alert mechanism

Arguments:
    ticker - Comapny stock ticker
    url - URL to an SEC filing
'''
def send_email(ticker, url):
    with open('config.json') as json_file:
        config = json.load(json_file)

    msg = EmailMessage()
    msg.set_content('Ticker: {}\nURL: {}'.format(ticker, url))

    msg['Subject'] = 'Bitcoin mentioned in company filing'
    msg['From'] = config['sendingEmailAddress']
    msg['To'] = config['receivingEmailAddress']

    s = smtplib.SMTP(config['smtpServer'], config['smtpPort'])
    s.starttls()
    s.login(config['sendingEmailAddress'], config['emailAppToken'])

    try:
        s.send_message(msg)
    except:
        print('Could not send email!')

    s.quit()


sio = socketio.Client()

# Event - Connect to API server 
@sio.on('connect', namespace='/all-filings')
def on_connect():
    print("Connected to https://api.sec-api.io:3334/all-filings")

# Event - Receive a new filing
@sio.on('filing', namespace='/all-filings')
def on_filings(filing):
    form_type = filing['formType']
    if form_type in RELEVANT_FORMS:
        url = filing['linkToHtml']
        if mentions_bitcoin(url):
            ticker = filing['ticker']
            send_email(ticker, url)

try:
    with open('config.json') as json_file:
        config = json.load(json_file)

    conn_str = 'https://api.sec-api.io:3334?apiKey={}'.format(config['apiKey'])
    sio.connect(conn_str, namespaces=['/all-filings'])
    sio.wait()
except Exception as e:
    print(e)
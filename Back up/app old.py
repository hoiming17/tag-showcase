from flask import Flask, request, render_template, redirect
import requests
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)
DATA_FILE = 'cards.json'

# --- helpers to load/save cards ---
def load_cards():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_cards(cards):
    with open(DATA_FILE, 'w') as f:
        json.dump(cards, f, indent=2)

# --- scraper for TAG page ---
def fetch_card_data(cert):
    url = f'https://my.taggrading.com/card/{cert}'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # ⚠️ These CSS selectors are just placeholders!
    # We'll update them after checking the real page structure
    name = soup.select_one('h1').text.strip() if soup.select_one('h1') else "Unknown Card"
    img = soup.select_one('img')['src'] if soup.select_one('img') else ""
    set_info = "Unknown Set"
    price = "N/A"

    return dict(cert=cert, name=name, img=img, set=set_info, price=price)

# --- routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    cards = load_cards()
    if request.method == 'POST':
        cert = request.form.get('cert').strip()
        data = fetch_card_data(cert)
        cards.append(data)
        save_cards(cards)
        return redirect('/')
    return render_template('index.html', cards=cards)

if __name__ == '__main__':
    app.run(debug=True)

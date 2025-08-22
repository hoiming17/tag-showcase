# app.py

import requests
from bs4 import BeautifulSoup
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def scrape_card_data(cert_number):
    """
    Scrapes a single TAG Grading card page for key information.
    """
    url = f"https://my.taggrading.com/card/{cert_number}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return {"error": "Failed to fetch card data. Please check the cert number."}

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Use the CSS selector to find the container div for all card info
    card_info_container = soup.find('div', class_=re.compile(r'jss141'))
    if not card_info_container:
        return {"error": "Could not find card information on the page. The cert number may be invalid."}

    # Find the data using the provided HTML structure
    data = {}
    
    # Player Name
    player_name_span = card_info_container.find('span', class_=re.compile(r'jss144'))
    data['player_name'] = player_name_span.get_text(strip=True) if player_name_span else 'N/A'

    # Set Name
    set_name_div = card_info_container.find('div', class_=re.compile(r'jss145'))
    if set_name_div:
        # The set name is the text node after the "Set name:" span
        set_name_text = ''.join(set_name_div.find('span', text='Set name:').next_siblings).strip()
        data['set_name'] = set_name_text if set_name_text else 'N/A'
    else:
        data['set_name'] = 'N/A'
        
    # Subset
    subset_div = card_info_container.find('div', class_=re.compile(r'jss146'))
    if subset_div:
        subset_text = ''.join(subset_div.find('span', text='Subset:').next_siblings).strip()
        data['subset'] = subset_text if subset_text and subset_text != '-' else 'N/A'
    else:
        data['subset'] = 'N/A'

    # Variation
    variation_div = card_info_container.find('div', class_=re.compile(r'jss148'))
    if variation_div:
        variation_text = ''.join(variation_div.find('span', text='Variation:').next_siblings).strip()
        data['variation'] = variation_text if variation_text and variation_text != '-' else 'N/A'
    else:
        data['variation'] = 'N/A'

    # TAG Score, Grade, and Grade Name
    tag_score_div = soup.find('div', class_=re.compile(r'jss153'))
    data['tag_score'] = tag_score_div.get_text(strip=True) if tag_score_div else 'N/A'
    
    grade_div = soup.find('div', class_=re.compile(r'jss157'))
    data['grade'] = grade_div.get_text(strip=True) if grade_div else 'N/A'

    grade_name_div = soup.find('div', class_=re.compile(r'jss158'))
    data['grade_name'] = grade_name_div.get_text(strip=True) if grade_name_div else 'N/A'

    return data

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    """Handles the scrape request from the front-end."""
    cert_number = request.json.get('cert_number')
    if not cert_number:
        return jsonify({"error": "No cert number provided."}), 400
    
    scraped_data = scrape_card_data(cert_number)
    return jsonify(scraped_data)

if __name__ == '__main__':
    # Use a dynamic port for Render deployment
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
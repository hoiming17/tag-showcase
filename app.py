# app.py

import requests
from bs4 import BeautifulSoup
import re
import logging
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

def scrape_card_data(cert_number):
    """
    Scrapes a single TAG Grading card page for key information.
    """
    url = f"https://my.taggrading.com/card/{cert_number}"
    logging.info(f"Attempting to scrape URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logging.info(f"Successfully fetched page for {cert_number}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching page for {cert_number}: {e}")
        return {"error": "Failed to fetch card data. Please check the cert number or URL."}

    soup = BeautifulSoup(response.text, 'html.parser')
    data = {}
    
    # --- Find Player Name, Set Name, Subset, and Variation ---
    # These are all in a span immediately following the anchor span
    
    try:
        # Player Name
        player_name_anchor = soup.find('span', string='Player name:')
        data['player_name'] = player_name_anchor.find_next_sibling('span').get_text(strip=True)
    except AttributeError:
        data['player_name'] = 'N/A'
        logging.warning("Player name not found.")

    try:
        # Set Name
        set_name_anchor = soup.find('span', string='Set name:')
        data['set_name'] = set_name_anchor.next_sibling.strip()
    except AttributeError:
        data['set_name'] = 'N/A'
        logging.warning("Set name not found.")
        
    try:
        # Subset
        subset_anchor = soup.find('span', string='Subset:')
        subset_val = subset_anchor.next_sibling.strip()
        data['subset'] = subset_val if subset_val and subset_val != '-' else 'N/A'
    except AttributeError:
        data['subset'] = 'N/A'
        logging.warning("Subset not found.")
        
    try:
        # Variation
        variation_anchor = soup.find('span', string='Variation:')
        variation_val = variation_anchor.next_sibling.strip()
        data['variation'] = variation_val if variation_val and variation_val != '-' else 'N/A'
    except AttributeError:
        data['variation'] = 'N/A'
        logging.warning("Variation not found.")

    # --- Find TAG Score, Grade, and Grade Name ---
    # These are in divs near the "TAG Score" text
    
    try:
        tag_score_div = soup.find('div', string=re.compile(r'TAG Score'))
        if tag_score_div:
            # The score is in the div right before the anchor div's parent
            parent_div = tag_score_div.find_parent('div')
            score_div = parent_div.find_previous_sibling('div').find('div')
            data['tag_score'] = score_div.get_text(strip=True)

            # The grade is a sibling of the score parent
            grade_container = parent_div.find_next_sibling('div')
            data['grade'] = grade_container.find('div').get_text(strip=True)
            data['grade_name'] = grade_container.find_all('div')[-1].get_text(strip=True)
    except AttributeError:
        logging.warning("TAG Score or Grade data not found.")
        data['tag_score'] = 'N/A'
        data['grade'] = 'N/A'
        data['grade_name'] = 'N/A'

    logging.info(f"Finished scraping. Data collected: {data}")
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
        logging.error("No cert number provided in the request.")
        return jsonify({"error": "No cert number provided."}), 400
    
    scraped_data = scrape_card_data(cert_number)
    return jsonify(scraped_data)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
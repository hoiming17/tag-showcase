# app.py

import requests
from bs4 import BeautifulSoup
import re
import logging
from flask import Flask, render_template, request, jsonify

# Configure logging to show messages in the console (Render's logs)
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
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)
        logging.info(f"Successfully fetched page for {cert_number}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching page for {cert_number}: {e}")
        return {"error": "Failed to fetch card data. Please check the cert number or URL."}

    soup = BeautifulSoup(response.text, 'html.parser')
    
    data = {}
    
    # Use the CSS selector to find the container div for all card info
    card_info_container = soup.find('div', class_=re.compile(r'jss\d+'))
    if not card_info_container:
        logging.warning("Could not find card information container. Selectors may be outdated.")
        return {"error": "Could not find card information on the page. The cert number may be invalid."}

    # Find the data using the provided HTML structure
    player_name_span = card_info_container.find('span', class_=re.compile(r'jss\d+'))
    if player_name_span:
        data['player_name'] = player_name_span.get_text(strip=True)
    else:
        data['player_name'] = 'N/A'
        logging.warning("Player name selector failed to find the element.")
        
    set_name_div = card_info_container.find('div', class_=re.compile(r'jss\d+'))
    if set_name_div:
        set_name_span = set_name_div.find('span', text=re.compile(r'Set name:'))
        if set_name_span:
            set_name_text = ''.join(set_name_span.next_siblings).strip()
            data['set_name'] = set_name_text if set_name_text else 'N/A'
        else:
            data['set_name'] = 'N/A'
            logging.warning("Set name span not found.")
    else:
        data['set_name'] = 'N/A'
        logging.warning("Set name container div not found.")
        
    # Repeat the pattern for other fields
    subset_div = card_info_container.find('div', class_=re.compile(r'jss\d+'))
    if subset_div:
        subset_span = subset_div.find('span', text=re.compile(r'Subset:'))
        if subset_span:
            subset_text = ''.join(subset_span.next_siblings).strip()
            data['subset'] = subset_text if subset_text and subset_text != '-' else 'N/A'
        else:
            data['subset'] = 'N/A'
            logging.warning("Subset span not found.")
    else:
        data['subset'] = 'N/A'
        logging.warning("Subset container div not found.")
    
    variation_div = card_info_container.find('div', class_=re.compile(r'jss\d+'))
    if variation_div:
        variation_span = variation_div.find('span', text=re.compile(r'Variation:'))
        if variation_span:
            variation_text = ''.join(variation_span.next_siblings).strip()
            data['variation'] = variation_text if variation_text and variation_text != '-' else 'N/A'
        else:
            data['variation'] = 'N/A'
            logging.warning("Variation span not found.")
    else:
        data['variation'] = 'N/A'
        logging.warning("Variation container div not found.")

    tag_score_div = soup.find('div', class_=re.compile(r'jss\d+'))
    data['tag_score'] = tag_score_div.get_text(strip=True) if tag_score_div else 'N/A'
    if not tag_score_div: logging.warning("TAG Score div not found.")
    
    grade_div = soup.find('div', class_=re.compile(r'jss\d+'))
    data['grade'] = grade_div.get_text(strip=True) if grade_div else 'N/A'
    if not grade_div: logging.warning("Grade div not found.")

    grade_name_div = soup.find('div', class_=re.compile(r'jss\d+'))
    data['grade_name'] = grade_name_div.get_text(strip=True) if grade_name_div else 'N/A'
    if not grade_name_div: logging.warning("Grade name div not found.")

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
# app.py

import requests
from bs4 import BeautifulSoup
import re
import logging
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

def get_text_after_anchor(soup, anchor_text):
    """Finds an anchor span and returns the text of its next sibling or text node."""
    anchor_span = soup.find('span', text=re.compile(f'^{anchor_text}:'))
    if anchor_span:
        next_sibling = anchor_span.next_sibling
        if next_sibling and next_sibling.name:
            # If the sibling is an HTML tag, get its text
            return next_sibling.get_text(strip=True)
        elif next_sibling:
            # If the sibling is a text node
            return next_sibling.strip()
    return 'N/A'

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
    
    # Use the static text anchors to find the data
    data['player_name'] = get_text_after_anchor(soup, 'Player name')
    data['set_name'] = get_text_after_anchor(soup, 'Set name')
    data['subset'] = get_text_after_anchor(soup, 'Subset')
    data['variation'] = get_text_after_anchor(soup, 'Variation')
    
    # --- Special case for TAG Score, Grade, and Grade Name ---
    # We find the "TAG Score" anchor, then navigate to its parent, then to the siblings
    tag_score_anchor = soup.find('div', text=re.compile(r'TAG Score'))
    if tag_score_anchor:
        # Go up to the parent container
        score_parent_div = tag_score_anchor.parent
        if score_parent_div:
            # Find the div with the score (e.g., '100')
            score_div = score_parent_div.find('div', class_=re.compile(r'jss\d+'))
            data['tag_score'] = score_div.get_text(strip=True) if score_div else 'N/A'
            
            # Find the grade container which is a sibling of the score parent
            grade_container = score_parent_div.find_next_sibling('div')
            if grade_container:
                grade_div = grade_container.find('div', class_=re.compile(r'jss\d+'))
                data['grade'] = grade_div.get_text(strip=True) if grade_div else 'N/A'
                
                grade_name_div = grade_container.find('div', class_=re.compile(r'jss\d+'))
                data['grade_name'] = grade_name_div.get_text(strip=True) if grade_name_div else 'N/A'
            else:
                data['grade'] = 'N/A'
                data['grade_name'] = 'N/A'
    else:
        logging.warning("TAG Score anchor not found.")
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
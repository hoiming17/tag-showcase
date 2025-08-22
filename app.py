# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options # Import Options for Chrome
from selenium.common.exceptions import WebDriverException
import os
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'a_very_secret_key'

# --- Browserless Configuration ---
# IMPORTANT: Replace 'YOUR_API_KEY' with your actual Browserless API key
# You can also store this in an environment variable on Render for security:
# BROWSERLESS_API_KEY = os.environ.get('BROWSERLESS_API_KEY', 'YOUR_API_KEY')
# BROWSERLESS_URL = f"https://chrome.browserless.io/webdriver?token={BROWSERLESS_API_KEY}"
BROWSERLESS_URL = "https://production-sfo.browserless.io/webdriver?token=2SuXmL5VzNoK49g3ef51708a0844cbbb2e883538fcb2e02d8"


# --- Helper Functions ---
def load_users():
    """Loads user data from the JSON file, handling potential errors."""
    if os.path.exists('users.json') and os.path.getsize('users.json') > 0:
        try:
            with open('users.json', 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Error: users.json file is corrupted. Returning an empty user list.")
            return {}
    return {}

def save_users(users_data):
    """Saves user data to the JSON file."""
    with open('users.json', 'w') as f:
        json.dump(users_data, f, indent=4)

# --- UPDATED scrape_card_info function to use Browserless ---
def scrape_card_info(cert_number):
    url = f"https://my.taggrading.com/card/{cert_number}"
    logger.info(f"Starting scrape for {cert_number} from URL: {url} using Browserless.")

     options = Options()
    # These are still recommended
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # This is the modern, preferred way to set headless mode
    options.headless = True
    
    driver = None
    try:
        # Connect to the remote Browserless service
        driver = webdriver.Remote(
            command_executor=BROWSERLESS_URL,
            options=options
        )
        
        # Set a reasonable page load timeout
        driver.set_page_load_timeout(30)
        
        driver.get(url)
        logger.info("Page loaded successfully via Browserless. Waiting for dynamic content.")
        time.sleep(3) # Give time for JavaScript to render
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        logger.info("Page source obtained and parsed.")

        line1, line2, line_subset, line3, line4 = "", "", "", "", ""

        try:
            player_label = soup.find("span", string="Player name:")
            if player_label:
                line1 = player_label.next_sibling.get_text(strip=True)
                logger.info(f"Scraped Player Name: {line1}")
            else:
                logger.warning("Player name label not found.")
        except Exception as e:
            logger.error(f"Error scraping Player Name: {e}")

        try:
            set_name_label = soup.find("span", string="Set name:")
            if set_name_label:
                line2 = set_name_label.next_sibling.get_text(strip=True)
                logger.info(f"Scraped Set Name: {line2}")
            else:
                logger.warning("Set name label not found.")
        except Exception as e:
            logger.error(f"Error scraping Set Name: {e}")

        try:
            subset_label = soup.find("span", string="Subset:")
            if subset_label:
                line_subset = subset_label.next_sibling.get_text(strip=True)
                if line_subset == "-": line_subset = ""
                logger.info(f"Scraped Subset: {line_subset}")
            else:
                logger.warning("Subset label not found.")
        except Exception as e:
            logger.error(f"Error scraping Subset: {e}")
            
        try:
            variation_label = soup.find("span", string="Variation:")
            if variation_label:
                line3 = variation_label.next_sibling.get_text(strip=True)
                if line3 == "-": line3 = ""
                logger.info(f"Scraped Variation: {line3}")
            else:
                logger.warning("Variation label not found.")
        except Exception as e:
            logger.error(f"Error scraping Variation: {e}")

        try:
            grade_anchor = soup.find("div", string="View Score")
            if grade_anchor:
                grade_container = grade_anchor.parent.find_next_sibling("div")
                if grade_container:
                    grade_number_div = grade_container.find("div")
                    grade_text_div = grade_number_div.find_next_sibling("div")
                    if grade_number_div and grade_text_div:
                        grade_number = grade_number_div.get_text(strip=True)
                        grade_text = grade_text_div.get_text(strip=True)
                        line4 = f"{grade_number} {grade_text}"
                        logger.info(f"Scraped Grade (View Score): {line4}")
                    else:
                        logger.warning("View Score child divs not found.")
            else:
                tag_score_anchor = soup.find("div", string="TAG Score")
                if tag_score_anchor:
                    tag_score_num_div = tag_score_anchor.find_previous_sibling("div")
                    tag_score_num = tag_score_num_div.get_text(strip=True) if tag_score_num_div else ""
                    grade_container = tag_score_anchor.parent.find_next_sibling("div")
                    if grade_container:
                        grade_divs = grade_container.find_all("div", recursive=False)
                        if len(grade_divs) >= 2:
                            grade_number = grade_divs[0].get_text(strip=True)
                            grade_text = grade_divs[1].get_text(strip=True)
                            line4 = f"{grade_number} {grade_text} ({tag_score_num})"
                            logger.info(f"Scraped Grade (TAG Score): {line4}")
                        else:
                            logger.warning("TAG Score child divs not found.")
                else:
                    logger.warning("Neither 'View Score' nor 'TAG Score' anchor found.")
        except Exception as e:
            line4 = ""
            logger.error(f"Error scraping grade info: {e}")

    except WebDriverException as e:
        logger.error(f"WebDriverException occurred during Browserless scrape: {e}")
        return {
            "cert_number": cert_number, "line1": "", "line2": "", "line_subset": "", 
            "line3": "", "line4": "", "hashtags": [],
            "image": f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg",
            "link": url
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred during the Browserless scrape process: {e}")
        return {
            "cert_number": cert_number, "line1": "", "line2": "", "line_subset": "", 
            "line3": "", "line4": "", "hashtags": [],
            "image": f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg",
            "link": url
        }
    finally:
        if driver:
            driver.quit()
            logger.info("Browserless driver closed.")

    image_url = f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg"
    logger.info(f"Scrape completed. Result: Player: {line1}, Set: {line2}, Grade: {line4}")
    return {
        "cert_number": cert_number, "line1": line1, "line2": line2, "line_subset": line_subset,
        "line3": line3, "line4": line4, "hashtags": [], "image": image_url, "link": url
    }

def get_grade_for_sort(card):
    line4 = card.get('line4', '')
    if not line4:
        return -1
    try:
        return float(line4.split()[0])
    except (ValueError, IndexError):
        return -1

# --- Routes ---
@app.route("/")
def index():
    if 'username' in session:
        return redirect(url_for('showcase', username=session['username']))
    return render_template('login.html')

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    users = load_users()
    if username in users:
        return "Username already exists. Please choose a different one."
    
    hashed_password = generate_password_hash(password)
    users[username] = {"password": hashed_password, "collection": [], "is_admin": False}
    save_users(users)
    return redirect(url_for('index'))

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    users = load_users()
    user_data = users.get(username)
    if user_data and check_password_hash(user_data["password"], password):
        session['username'] = username
        if user_data.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('showcase', username=username))
    return "Invalid username or password."

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/showcase/<username>")
def showcase(username):
    users = load_users()
    all_users = list(users.keys())
    
    if username not in users:
        return "User not found.", 404

    full_collection = users[username]["collection"]
    all_hashtags = {tag for card in full_collection for tag in card.get('hashtags', [])}
    active_hashtag = request.args.get('hashtag')
    
    if active_hashtag:
        filtered_collection = [card for card in full_collection if active_hashtag in card.get('hashtags', [])]
    else:
        filtered_collection = full_collection

    sort_by = request.args.get('sort_by', 'default')
    if sort_by == 'grade':
        filtered_collection.sort(key=get_grade_for_sort, reverse=True)
    elif sort_by == 'set_name':
        filtered_collection.sort(key=lambda card: card.get('line2', ''))

    total_cards = len(full_collection)
    grade_counts = {}
    for card in full_collection:
        grade = card.get('line4', '').split()[0] if card.get('line4') else 'N/A'
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    logged_in_user_data = users.get(session.get('username'))
    is_admin = logged_in_user_data.get('is_admin', False) if logged_in_user_data else False
    is_owner = (session.get('username') == username) or is_admin

    return render_template(
        'showcase.html', 
        logged_in_user=session.get('username'), 
        displayed_user=username,
        all_users=all_users,
        collection=filtered_collection,
        is_owner=is_owner,
        is_admin=is_admin,
        current_sort=sort_by,
        all_hashtags=sorted(list(all_hashtags)),
        active_hashtag=active_hashtag,
        total_cards=total_cards,
        grade_counts=grade_counts
    )

@app.route("/admin")
def admin_dashboard():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data or not logged_in_user_data.get('is_admin'):
        return "Access Denied: Admin role required.", 403
    
    all_users = list(users.keys())
    return render_template('admin_dashboard.html', all_users=all_users)

@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data or not logged_in_user_data.get('is_admin'):
        return "Access Denied: Admin role required.", 403
    
    username = request.form["username"]
    password = request.form["password"]

    if username in users:
        return "Username already exists. Please choose a different one.", 400

    hashed_password = generate_password_hash(password)
    users[username] = {"password": hashed_password, "collection": [], "is_admin": False}
    save_users(users)
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/remove_user", methods=["POST"])
def admin_remove_user():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data or not logged_in_user_data.get('is_admin'):
        return "Access Denied: Admin role required.", 403

    username = request.form["username"]
    if username in users and username != 'admin':
        del users[username]
        save_users(users)
    
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/change_password", methods=["POST"])
def admin_change_password():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data or not logged_in_user_data.get('is_admin'):
        return "Access Denied: Admin role required.", 403

    username = request.form["username"]
    new_password = request.form["new_password"]

    if username in users:
        users[username]["password"] = generate_password_hash(new_password)
        save_users(users)
    
    return redirect(url_for('admin_dashboard'))

@app.route("/add_hashtag", methods=["POST"])
def add_hashtag():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    cert_number = request.form.get("cert_number").strip()
    hashtag = request.form.get("hashtag").strip().lower()
    target_username = request.form.get("target_username") or session['username']

    if not logged_in_user_data.get('is_admin') and target_username != session['username']:
        return jsonify({"success": False, "message": "You can only edit your own collection."}), 403

    if not hashtag or not cert_number:
        return jsonify({"success": False, "message": "Missing card or hashtag."}), 400

    user_data = users.get(target_username)
    if not user_data:
        return jsonify({"success": False, "message": "Target user not found."}), 404
    
    for card in user_data['collection']:
        if card["cert_number"] == cert_number:
            if 'hashtags' not in card:
                card['hashtags'] = []
            if hashtag not in card['hashtags']:
                card['hashtags'].append(hashtag)
                save_users(users)
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "message": "Hashtag already exists on this card."})
    
    return jsonify({"success": False, "message": "Card not found."}), 404

@app.route("/remove_hashtag", methods=["POST"])
def remove_hashtag():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data:
        return jsonify({"success": False, "message": "Not logged in."}), 401

    cert_number = request.form.get("cert_number").strip()
    hashtag = request.form.get("hashtag").strip().lower()
    target_username = request.form.get("target_username") or session['username']

    if not logged_in_user_data.get('is_admin') and target_username != session['username']:
        return jsonify({"success": False, "message": "You can only edit your own collection."}), 403

    if not hashtag or not cert_number:
        return jsonify({"success": False, "message": "Missing card or hashtag."}), 400
    
    user_data = users.get(target_username)
    if not user_data:
        return jsonify({"success": False, "message": "Target user not found."}), 404

    for card in user_data['collection']:
        if card["cert_number"] == cert_number:
            if 'hashtags' in card and hashtag in card['hashtags']:
                card['hashtags'].remove(hashtag)
                save_users(users)
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "message": "Hashtag not found on this card."})
    
    return jsonify({"success": False, "message": "Card not found."}), 404

@app.route("/add", methods=["POST"])
def add():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data:
        return redirect(url_for('index'))

    cert_number = request.form["cert_number"].strip()
    target_username = request.form.get("target_username") or session['username']
    
    if not logged_in_user_data.get('is_admin') and target_username != session['username']:
        return "You can only edit your own collection.", 403

    user_data = users.get(target_username)
    if not user_data:
        return "Target user not found.", 404
    
    if any(card['cert_number'] == cert_number for card in user_data['collection']):
        return "Card already in collection."
        
    card_info = scrape_card_info(cert_number)
    user_data['collection'].append(card_info)
    save_users(users)
    
    return redirect(url_for('showcase', username=target_username))

@app.route("/remove", methods=["POST"])
def remove():
    users = load_users()
    logged_in_user_data = users.get(session.get('username'))
    if not logged_in_user_data:
        return redirect(url_for('index'))
    
    cert_number = request.form["cert_number"].strip()
    target_username = request.form.get("target_username") or session['username']

    if not logged_in_user_data.get('is_admin') and target_username != session['username']:
        return "You can only edit your own collection.", 403
    
    user_data = users.get(target_username)
    if not user_data:
        return "Target user not found.", 404
    
    user_data['collection'] = [c for c in user_data['collection'] if c["cert_number"] != cert_number]
    save_users(users)
    
    return redirect(url_for('showcase', username=target_username))

if __name__ == "__main__":
    app.run(debug=True)
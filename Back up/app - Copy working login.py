from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os

app = Flask(__name__)
app.secret_key = 'a_very_secret_key'

def load_users():
    """Loads user data from the JSON file, handling empty files."""
    if os.path.exists('users.json') and os.path.getsize('users.json') > 0:
        with open('users.json', 'r') as f:
            return json.load(f)
    return {}

def save_users(users_data):
    """Saves user data to the JSON file."""
    with open('users.json', 'w') as f:
        json.dump(users_data, f, indent=4)

def scrape_card_info(cert_number):
    url = f"https://my.taggrading.com/card/{cert_number}"
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(3)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        line1, line2, line_subset, line3, line4 = "", "", "", "", ""
        
        try:
            player_label = soup.find("span", string="Player name:")
            if player_label and player_label.find_next_sibling("span"):
                line1 = player_label.find_next_sibling("span").get_text(strip=True)
        except Exception:
            pass

        try:
            set_name_label = soup.find("span", string="Set name:")
            if set_name_label and set_name_label.parent:
                set_name_full_text = set_name_label.parent.get_text(strip=True)
                line2 = set_name_full_text.replace("Set name:", "").strip()
        except Exception:
            pass
        
        try:
            subset_label = soup.find("span", string="Subset:")
            if subset_label and subset_label.parent:
                subset_full_text = subset_label.parent.get_text(strip=True)
                line_subset = subset_full_text.replace("Subset:", "").strip()
                if line_subset == "-":
                    line_subset = ""
        except Exception:
            pass

        try:
            variation_label = soup.find("span", string="Variation:")
            if variation_label and variation_label.parent:
                variation_full_text = variation_label.parent.get_text(strip=True)
                line3 = variation_full_text.replace("Variation:", "").strip()
                if line3 == "-":
                    line3 = ""
        except Exception:
            pass

        try:
            grade_anchor = soup.find("div", string="View Score")
            if grade_anchor:
                common_container = grade_anchor.parent.parent
                grade_container = common_container.find_all("div", recursive=False)[1]
                grade_number_div = grade_container.find("div")
                grade_text_div = grade_number_div.find_next_sibling("div")
                
                if grade_number_div and grade_text_div:
                    grade_number = grade_number_div.get_text(strip=True)
                    grade_text = grade_text_div.get_next_sibling("div").get_text(strip=True) if grade_number_div.find_next_sibling("div").get_text(strip=True).isdigit() else grade_text_div.get_text(strip=True)
                    line4 = f"{grade_number} {grade_text}"
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
                            
        except Exception as e:
            line4 = ""

    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            "cert_number": cert_number, "line1": "", "line2": "", "line_subset": "", 
            "line3": "", "line4": "", 
            "image": f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg",
            "link": url
        }
    finally:
        if driver:
            driver.quit()

    image_url = f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg"
    return {
        "cert_number": cert_number, "line1": line1, "line2": line2, "line_subset": line_subset,
        "line3": line3, "line4": line4, "image": image_url, "link": url
    }

# A helper function to extract a float grade for sorting
def get_grade_for_sort(card):
    line4 = card.get('line4', '')
    if not line4:
        return -1  # Use -1 for cards with no grade, so they appear last

    try:
        # Extract the numeric part of the grade (e.g., "10" from "10 Pristine")
        return float(line4.split()[0])
    except (ValueError, IndexError):
        return -1 # Handle cases where grade is not a simple number

# --- Routes ---
@app.route("/")
def index():
    try:
        if 'username' in session:
            username = session['username']
            users = load_users()
            if username in users:
                return redirect(url_for('showcase', username=username))
            else:
                session.clear()
    except KeyError:
        session.clear()
    
    return render_template('login.html')

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    users = load_users()
    if username in users:
        return "Username already exists. Please choose a different one."
    
    hashed_password = generate_password_hash(password)
    users[username] = {"password": hashed_password, "collection": []}
    save_users(users)
    return redirect(url_for('index'))

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    users = load_users()
    if username in users and check_password_hash(users[username]["password"], password):
        session['username'] = username
        return redirect(url_for('showcase', username=username))
    return "Invalid username or password."

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/showcase/<username>")
def showcase(username):
    if 'username' not in session:
        return redirect(url_for('index'))

    users = load_users()
    all_users = list(users.keys())
    
    if username not in users:
        return "User not found.", 404

    # The collection to display
    displayed_collection = users[username]["collection"]
    
    # Get the sort parameter from the URL (e.g., ?sort_by=grade)
    sort_by = request.args.get('sort_by', 'default')

    if sort_by == 'grade':
        # Sort by grade number, descending
        displayed_collection = sorted(displayed_collection, key=get_grade_for_sort, reverse=True)
    elif sort_by == 'set_name':
        # Sort by set name, ascending
        displayed_collection = sorted(displayed_collection, key=lambda card: card.get('line2', ''))

    is_owner = (session['username'] == username)

    return render_template(
        'showcase.html', 
        logged_in_user=session['username'], 
        displayed_user=username,
        all_users=all_users,
        collection=displayed_collection,
        is_owner=is_owner,
        current_sort=sort_by
    )

@app.route("/add", methods=["POST"])
def add():
    if 'username' not in session:
        return redirect(url_for('index'))

    cert_number = request.form["cert_number"].strip()
    users = load_users()
    user_data = users[session['username']]
    
    if any(card['cert_number'] == cert_number for card in user_data['collection']):
        return "Card already in collection."
        
    card_info = scrape_card_info(cert_number)
    user_data['collection'].append(card_info)
    save_users(users)
    
    return redirect(url_for('showcase', username=session['username']))

@app.route("/remove", methods=["POST"])
def remove():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    cert_number = request.form["cert_number"].strip()
    users = load_users()
    user_data = users[session['username']]
    
    user_data['collection'] = [c for c in user_data['collection'] if c["cert_number"] != cert_number]
    save_users(users)
    
    return redirect(url_for('showcase', username=session['username']))

if __name__ == "__main__":
    app.run(debug=True)
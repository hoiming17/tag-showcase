from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
# CHANGE IS HERE: We need to explicitly point to the Service.
from selenium.webdriver.chrome.service import Service
import os
import time
import json

app = Flask(__name__)
app.secret_key = 'a_very_secret_key'

# --- Helper Functions ---
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

    # We get the path from the environment variable set in the Dockerfile
    # This is the key change for container compatibility
    chrome_executable_path = os.environ.get('CHROMIUM_EXECUTABLE_PATH')
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox") # Required for Docker
    options.add_argument("--disable-dev-shm-usage") # Required for Docker
    options.add_argument("--log-level=3")
    
    # We pass the executable path directly to the Service
    service = Service(executable_path=chrome_executable_path)
    
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
                    grade_text = grade_text_div.get_text(strip=True)
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
            "line3": "", "line4": "", "hashtags": [],
            "image": f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg",
            "link": url
        }
    finally:
        if driver:
            driver.quit()

    image_url = f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg"
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
        # User is logged in, redirect to their showcase
        return redirect(url_for('showcase', username=session['username']))
    
    # User is not logged in, show the login page
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
    
    all_hashtags = set()
    for card in full_collection:
        all_hashtags.update(card.get('hashtags', []))

    active_hashtag = request.args.get('hashtag')
    if active_hashtag:
        filtered_collection = [card for card in full_collection if active_hashtag in card.get('hashtags', [])]
    else:
        filtered_collection = full_collection

    sort_by = request.args.get('sort_by', 'default')
    if sort_by == 'grade':
        filtered_collection = sorted(filtered_collection, key=get_grade_for_sort, reverse=True)
    elif sort_by == 'set_name':
        filtered_collection = sorted(filtered_collection, key=lambda card: card.get('line2', ''))

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
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import hashlib # For basic password hashing

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this_for_production' # Needed for Flask sessions

# File paths for user data and collections
USERS_FILE = 'users.json'
COLLECTIONS_FILE = 'collections.json'

# --- Helper functions for JSON file operations ---
def load_json_file(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump({}, f)
        return {}
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {filename}. Resetting file.")
            with open(filename, 'w') as f:
                json.dump({}, f)
            return {}

def save_json_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def hash_password(password):
    # WARNING: SHA256 is NOT suitable for strong password hashing in production.
    # Use libraries like 'bcrypt' or 'passlib' for real applications.
    return hashlib.sha256(password.encode()).hexdigest()

# --- Card Scraping Logic (remains largely the same) ---
def scrape_card_info(cert_number):
    url = f"https://my.taggrading.com/card/{cert_number}"
    
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") # Run in headless mode (no visible browser window)
    options.add_argument("--log-level=3") # Suppress log messages
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(3) # Wait for the JavaScript to load the content
        
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
        print(f"An error occurred during scraping: {e}")
        return {
            "error": str(e),
            "cert_number": cert_number,
            "line1": "", "line2": "", "line_subset": "", "line3": "", "line4": "",
            "image": f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg",
            "link": url
        }
    finally:
        if driver:
            driver.quit()

    image_url = f"https://devblock-tag.s3.us-west-2.amazonaws.com/slab-images/{cert_number}_Slabbed_FRONT.jpg"

    return {
        "cert_number": cert_number,
        "line1": line1,
        "line2": line2,
        "line_subset": line_subset,
        "line3": line3,
        "line4": line4,
        "image": image_url,
        "link": url
    }

# --- Flask Routes ---

# Main HTML template
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Card Collection</title>
    <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Open Sans', sans-serif; 
            margin: 0; 
            background-color: black; 
            color: white; 
            font-size: 75%;
            display: flex; /* Flexbox for main body layout */
            min-height: 100vh;
        }
        .login-register-container, .main-content {
            flex-grow: 1; /* Allow these containers to take available space */
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .auth-status {
            font-size: 0.8em;
            text-align: right;
        }
        .auth-form {
            background-color: #333;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            max-width: 400px;
            margin-left: auto;
            margin-right: auto;
        }
        .auth-form input[type="text"],
        .auth-form input[type="password"] {
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            border: 1px solid #555;
            background-color: #444;
            color: white;
            width: 100%;
            box-sizing: border-box;
        }
        .auth-form button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        .auth-form button:hover {
            background-color: #45a049;
        }
        .card-form {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #2a2a2a;
            border-radius: 8px;
        }
        .card-form input[type="text"] {
            padding: 8px;
            margin-right: 10px;
            border-radius: 4px;
            border: 1px solid #555;
            background-color: #444;
            color: white;
            width: calc(100% - 120px);
            box-sizing: border-box;
        }
        .card-form button {
            background-color: #007bff;
            color: white;
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .card-form button:hover {
            background-color: #0056b3;
        }
        .card-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }
        .card { 
            border: 1px solid #444; 
            padding: 10px; 
            background-color: #1a1a1a;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            width: 200px; 
            min-height: 400px; 
        }
        img { 
            display: block;
            margin: 0 auto 10px auto; 
            max-width: 100%; 
            border-radius: 4px;
        }
        .card p {
            margin: 0;
            line-height: 1.2; 
            padding-bottom: 2px; 
        }
        .card p:last-of-type {
            margin-bottom: 10px; 
        }
        .card strong {
            font-weight: 700;
        }
        .card a {
            color: #88c0d0;
            text-decoration: none;
            word-break: break-all; 
        }
        .card a:hover {
            text-decoration: underline;
        }
        .card-actions {
            margin-top: auto; 
            display: flex;
            justify-content: center;
        }
        .card-actions button {
            background-color: #dc3545;
            color: white;
            padding: 6px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .card-actions button:hover {
            background-color: #c82333;
        }
        .message {
            background-color: #ffc107;
            color: #333;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            text-align: center;
        }
        /* Side Navigation */
        .side-nav {
            width: 200px;
            background-color: #222;
            padding: 20px 10px;
            box-shadow: 2px 0 5px rgba(0,0,0,0.5);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #444;
        }
        .side-nav h2 {
            color: #fff;
            margin-top: 0;
            font-size: 1.2em;
            text-align: center;
            border-bottom: 1px solid #444;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .side-nav ul {
            list-style: none;
            padding: 0;
            margin: 0;
            flex-grow: 1;
            overflow-y: auto;
        }
        .side-nav li {
            margin-bottom: 8px;
        }
        .side-nav a {
            color: #88c0d0;
            text-decoration: none;
            display: block;
            padding: 5px 10px;
            border-radius: 4px;
        }
        .side-nav a:hover, .side-nav a.active {
            background-color: #444;
            color: white;
        }
        .current-user-info {
            margin-top: auto;
            font-size: 0.7em;
            color: #777;
            word-break: break-all;
            padding-top: 15px;
            border-top: 1px solid #444;
            text-align: center;
        }
        .sorting-controls {
            margin-bottom: 15px;
            text-align: center;
            background-color: #2a2a2a;
            padding: 10px;
            border-radius: 8px;
        }
        .sorting-controls button {
            background-color: #6c757d;
            color: white;
            padding: 6px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 0 5px;
            font-size: 0.8em;
        }
        .sorting-controls button:hover {
            background-color: #5a6268;
        }
        .sorting-controls span {
            margin-right: 10px;
            color: #bbb;
        }
    </style>
    <script>
        // Client-side JavaScript logic
        let currentDisplayedUsername = null;
        let currentCollectionData = []; // Store fetched data for sorting
        let currentSortBy = 'cert_number'; // Default sort
        let loggedInUser = '{{ logged_in_user }}' ? '{{ logged_in_user }}' : null; // Get from Flask template

        function showMessage(type, text) {
            const messageBox = document.getElementById('message-box');
            if (messageBox) {
                messageBox.textContent = text;
                messageBox.style.backgroundColor = type === 'error' ? '#dc3545' : '#ffc107';
                messageBox.style.color = type === 'error' ? 'white' : '#333';
                messageBox.style.display = 'block';
            }
        }

        async function updateUI(loggedInUserParam, displayedUserParam) {
            const authStatusElement = document.getElementById('auth-status');
            const loginRegisterContainer = document.getElementById('login-register-container'); // New container for auth forms
            const loginSection = document.getElementById('login-section');
            const registerSection = document.getElementById('register-section');
            const mainContentArea = document.getElementById('main-content-area');
            const sideNav = document.getElementById('side-nav');
            const currentUserInfoDisplay = document.getElementById('current-user-info');
            const cardCollectionGrid = document.getElementById('card-collection-grid');
            const addCardSection = document.getElementById('add-card-section');
            const sortingControls = document.getElementById('sorting-controls');

            // Update global loggedInUser variable
            loggedInUser = loggedInUserParam;

            // Clear login/register form fields
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
            document.getElementById('register-username').value = '';
            document.getElementById('register-password').value = '';
            document.getElementById('message-box').textContent = '';

            if (loggedInUser) {
                // If logged in, show main content and hide auth forms
                authStatusElement.innerHTML = `Logged in as: ${loggedInUser} (<a href="/logout">Logout</a>)`;
                loginRegisterContainer.style.display = 'none';
                mainContentArea.style.display = 'flex'; // Main content area is now a flex container
                sideNav.style.display = 'flex';
                currentUserInfoDisplay.textContent = `You are: ${loggedInUser}`;

                // Set displayed user if not already set by URL (e.g., initial load on /collection/<username>)
                // or if redirected from login/register
                if (displayedUserParam) {
                    currentDisplayedUsername = displayedUserParam;
                } else {
                    currentDisplayedUsername = loggedInUser;
                    window.history.replaceState({}, '', `/collection/${loggedInUser}`); // Correct URL if on root after login
                }
                
                fetchCollection(currentDisplayedUsername);
                fetchAllUsersForNav(); // Fetch all users for side nav
            } else {
                // If not logged in, show auth forms and hide main content
                authStatusElement.innerHTML = `Not logged in (<a href="#" id="show-login-link">Login</a> | <a href="#" id="show-register-link">Register</a>)`;
                loginRegisterContainer.style.display = 'block'; // Show login/register forms container
                loginSection.style.display = 'block'; // Default to showing login
                registerSection.style.display = 'none';
                mainContentArea.style.display = 'none'; // Hide main collection content
                sideNav.style.display = 'none';
                cardCollectionGrid.innerHTML = '<p>Please log in to view collections.</p>';
            }

            // Show/hide add card form and remove buttons based on ownership and login status
            if (loggedInUser && loggedInUser === currentDisplayedUsername) {
                addCardSection.style.display = 'block';
                sortingControls.style.display = 'block';
            } else {
                addCardSection.style.display = 'none';
                sortingControls.style.display = 'block'; // Still allow sorting for others' pages
            }
        }

        async function fetchCollection(usernameToDisplay) {
            const collectionGrid = document.getElementById('card-collection-grid');
            const cardCountElement = document.getElementById('card-count');
            collectionGrid.innerHTML = '<p>Loading collection...</p>';
            cardCountElement.textContent = '0 cards';
            currentCollectionData = []; // Clear previous data

            try {
                const response = await fetch(`/get_user_collection/${usernameToDisplay}`);
                const data = await response.json();
                if (response.ok) {
                    currentCollectionData = data.cards || [];
                    renderCollection(currentCollectionData);
                } else {
                    showMessage('error', data.error || 'Failed to load collection.');
                    collectionGrid.innerHTML = '<p>Error loading collection.</p>';
                }
            } catch (error) {
                console.error("Error fetching collection:", error);
                showMessage('error', `Error loading collection: ${error.message}`);
                collectionGrid.innerHTML = '<p>Error loading collection.</p>';
            }
        }

        function renderCollection(cards) {
            const collectionGrid = document.getElementById('card-collection-grid');
            const cardCountElement = document.getElementById('card-count');
            collectionGrid.innerHTML = ''; // Clear existing cards

            let sortedCards = [...cards]; // Create a copy to sort

            if (currentSortBy === 'grade_number') {
                sortedCards.sort((a, b) => {
                    // Extract numerical part for sorting. Handle cases like "1 POOR (100)"
                    const getNumericalGrade = (gradeStr) => {
                        if (!gradeStr) return -Infinity; // Place cards without grade at the end
                        const match = gradeStr.match(/^(\d+(\.\d+)?)/);
                        return match ? parseFloat(match[1]) : -Infinity;
                    };
                    const gradeA = getNumericalGrade(a.line4);
                    const gradeB = getNumericalGrade(b.line4);
                    return gradeB - gradeA; // Sort descending
                });
            } else if (currentSortBy === 'player_name') {
                sortedCards.sort((a, b) => (a.line1 || '').localeCompare(b.line1 || ''));
            } else if (currentSortBy === 'set_name') {
                sortedCards.sort((a, b) => (a.line2 || '').localeCompare(b.line2 || ''));
            }

            if (sortedCards.length === 0) {
                collectionGrid.innerHTML = '<p>This collection is empty.</p>';
            } else {
                sortedCards.forEach(card => {
                    const cardElement = document.createElement('div');
                    cardElement.className = 'card';
                    // Check if current user owns this page to show remove button
                    const showRemove = (loggedInUser === currentDisplayedUsername); // Use global loggedInUser
                    cardElement.innerHTML = `
                        <img src="${card.image}" alt="Card image">
                        ${card.line1 ? `<p><strong>${card.line1}</strong></p>` : ''}
                        ${card.line2 ? `<p>${card.line2}</p>` : ''}
                        ${card.line_subset ? `<p>${card.line_subset}</p>` : ''}
                        ${card.line3 ? `<p>${card.line3}</p>` : ''}
                        ${card.line4 ? `<p>${card.line4}</p>` : ''}
                        <p><a href="${card.link}" target="_blank">${card.cert_number}</a></p>
                        ${showRemove ? `
                        <div class="card-actions">
                            <form class="remove-form" data-cert-number="${card.cert_number}">
                                <button type="submit">Remove</button>
                            </form>
                        </div>
                        ` : ''}
                    `;
                    collectionGrid.appendChild(cardElement);
                });
            }
            cardCountElement.textContent = `${sortedCards.length} cards`;
        }

        async function fetchAllUsersForNav() {
            const usersList = document.getElementById('users-list');
            usersList.innerHTML = '<p>Loading users...</p>';

            try {
                const response = await fetch('/get_all_users');
                const data = await response.json();
                if (response.ok) {
                    usersList.innerHTML = '';
                    if (data.users && data.users.length > 0) {
                        data.users.forEach(username => {
                            const userLi = document.createElement('li');
                            const activeClass = (username === currentDisplayedUsername) ? 'active' : '';
                            userLi.innerHTML = `
                                <li><a href="/collection/${username}" class="user-nav-link ${activeClass}" data-username="${username}">${username}</a></li>
                            `;
                            usersList.appendChild(userLi);
                        });
                    } else {
                        usersList.innerHTML = '<p>No other users yet.</p>';
                    }
                } else {
                    showMessage('error', data.error || 'Failed to load user list.');
                    usersList.innerHTML = '<p>Error loading user list.</p>';
                }
            } catch (error) {
                console.error("Error fetching user list:", error);
                showMessage('error', `Error loading user list: ${error.message}`);
                usersList.innerHTML = '<p>Error loading user list.</p>';
            }
        }

        // --- Event Listeners ---
        document.addEventListener('DOMContentLoaded', () => {
            const pathParts = window.location.pathname.split('/');
            const currentPathname = window.location.pathname;
            
            let displayedUserOnLoad = null;

            if (currentPathname.startsWith('/collection/') && pathParts.length > 2) {
                // If it's a /collection/username page
                displayedUserOnLoad = pathParts[2]; // Get username from URL
            } else {
                // If it's the root path, no specific user collection is displayed yet
                displayedUserOnLoad = null;
            }
            
            // Call updateUI with the current logged-in user from Flask and the user being displayed
            updateUI(loggedInUser, displayedUserOnLoad);
        });

        document.addEventListener('click', async (event) => {
            if (event.target.id === 'show-login-link') {
                event.preventDefault();
                document.getElementById('login-section').style.display = 'block';
                document.getElementById('register-section').style.display = 'none';
                document.getElementById('message-box').textContent = '';
            } else if (event.target.id === 'show-register-link') {
                event.preventDefault();
                document.getElementById('register-section').style.display = 'block';
                document.getElementById('login-section').style.display = 'none';
                document.getElementById('message-box').textContent = '';
            } else if (event.target.closest('.user-nav-link')) {
                event.preventDefault();
                const usernameToDisplay = event.target.closest('.user-nav-link').dataset.username;
                if (usernameToDisplay && usernameToDisplay !== currentDisplayedUsername) {
                    currentDisplayedUsername = usernameToDisplay;
                    window.history.pushState({}, '', `/collection/${currentDisplayedUsername}`);
                    // Re-render UI based on new displayed user and current logged-in user
                    await updateUI(loggedInUser, currentDisplayedUsername); 
                }
            } else if (event.target.classList.contains('sort-button')) {
                currentSortBy = event.target.dataset.sort;
                renderCollection(currentCollectionData); // Re-render with new sort order
            }
        });

        document.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent default form submission

            if (event.target.id === 'login-form') {
                const username = event.target.username.value;
                const password = event.target.password.value;
                try {
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `username=${username}&password=${password}`
                    });
                    const data = await response.json();
                    if (response.ok) {
                        showMessage('success', data.message);
                        // Store logged-in username globally and redirect
                        loggedInUser = username; 
                        window.location.href = `/collection/${username}`; 
                    } else {
                        showMessage('error', data.error || 'Login failed.');
                    }
                } catch (error) {
                    console.error("Login error:", error);
                    showMessage('error', `Login failed: ${error.message}`);
                }
            } else if (event.target.id === 'register-form') {
                const username = event.target.username.value;
                const password = event.target.password.value;
                try {
                    const response = await fetch('/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `username=${username}&password=${password}`
                    });
                    const data = await response.json();
                    if (response.ok) {
                        showMessage('success', data.message);
                        // Store logged-in username globally and redirect
                        loggedInUser = username;
                        window.location.href = `/collection/${username}`;
                    } else {
                        showMessage('error', data.error || 'Registration failed.');
                    }
                } catch (error) {
                    console.error("Registration error:", error);
                    showMessage('error', `Registration failed: ${error.message}`);
                }
            } else if (event.target.id === 'add-form') {
                const certNumberInput = document.getElementById('cert_number_input');
                const certNumber = certNumberInput.value;
                if (!loggedInUser || loggedInUser !== currentDisplayedUsername) { // Use global loggedInUser
                    showMessage('error', 'You can only add cards to your own collection.');
                    return;
                }
                try {
                    const response = await fetch('/add_card', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `cert_number=${certNumber}`
                    });
                    const data = await response.json();
                    if (response.ok) {
                        showMessage('success', data.message);
                        certNumberInput.value = ''; // Clear input
                        // Collection will be automatically re-rendered by fetchCollection which is called on page load/history change
                        fetchCollection(currentDisplayedUsername); // Explicitly refetch to update
                    } else {
                        showMessage('error', data.error || 'Failed to add card.');
                    }
                } catch (error) {
                    console.error("Add card error:", error);
                    showMessage('error', `Error adding card: ${error.message}`);
                }
            } else if (event.target.classList.contains('remove-form')) {
                const certNumberToRemove = event.target.dataset.certNumber;
                if (!loggedInUser || loggedInUser !== currentDisplayedUsername) { // Use global loggedInUser
                    showMessage('error', 'You can only remove cards from your own collection.');
                    return;
                }
                try {
                    const response = await fetch('/remove_card', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `cert_number=${certNumberToRemove}`
                    });
                    const data = await response.json();
                    if (response.ok) {
                        showMessage('success', data.message);
                        // Collection will be automatically re-rendered
                        fetchCollection(currentDisplayedUsername); // Explicitly refetch to update
                    } else {
                        showMessage('error', data.error || 'Failed to remove card.');
                    }
                } catch (error) {
                    console.error("Remove card error:", error);
                    showMessage('error', `Error removing card: ${error.message}`);
                }
            }
        });

        // Handle browser history changes (e.g., back/forward buttons)
        window.onpopstate = () => {
            const pathParts = window.location.pathname.split('/');
            const usernameInUrl = pathParts[pathParts.length - 1];
            
            if (window.location.pathname.startsWith('/collection/') && usernameInUrl) {
                currentDisplayedUsername = usernameInUrl;
                updateUI(loggedInUser, currentDisplayedUsername); // Use global loggedInUser
            } else {
                // If navigated back to / or invalid path, default to login or user's own page if logged in
                if (loggedInUser) {
                    window.history.replaceState({}, '', `/collection/${loggedInUser}`);
                    currentDisplayedUsername = loggedInUser;
                    updateUI(loggedInUser, currentDisplayedUsername); // Use global loggedInUser
                } else {
                    updateUI(null, null); // Show login page
                }
            }
        };

    </script>
</head>
<body>
    <aside class="side-nav" id="side-nav" style="display: none;">
        <h2>Users</h2>
        <ul id="users-list">
            <!-- User links will be populated here by JavaScript -->
        </ul>
        <div class="current-user-info" id="current-user-info"></div>
    </aside>

    <div class="login-register-container" id="login-register-container" style="display: block;">
        <div class="container">
            <div class="header">
                <h1>My Card Collection</h1>
                <div class="auth-status" id="auth-status"></div>
            </div>
            <div id="message-box" class="message" style="display: none;"></div>
            
            <div id="login-section" style="display: block;"> <!-- Default to login -->
                <h2>Login</h2>
                <form id="login-form" class="auth-form">
                    <input type="text" id="login-username" name="username" placeholder="Username" required>
                    <input type="password" id="login-password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                    <button type="button" id="show-register-link">Register</button>
                </form>
            </div>

            <div id="register-section" style="display: none;">
                <h2>Register</h2>
                <form id="register-form" class="auth-form">
                    <input type="text" id="register-username" name="username" placeholder="Username" required>
                    <input type="password" id="register-password" name="password" placeholder="Password" required>
                    <button type="submit">Register</button>
                    <button type="button" id="show-login-link">Login</button>
                </form>
            </div>
        </div>
    </div>

    <div class="main-content" id="main-content-area" style="display: none;">
        <div class="container">
            <div class="header">
                <h1>My Card Collection</h1>
                <div class="auth-status" id="auth-status-copy"></div> <!-- Added a copy for consistent header -->
            </div>

            <div id="message-box-copy" class="message" style="display: none;"></div> <!-- Added copy for message box -->
            
            <div id="collection-display-section">
                <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h2>Collection <span id="card-count">0 cards</span></h2>
                    <div class="sorting-controls" id="sorting-controls" style="display: none;">
                        <span>Sort by:</span>
                        <button class="sort-button" data-sort="grade_number">Grade</button>
                        <button class="sort-button" data-sort="player_name">Player Name</button>
                        <button class="sort-button" data-sort="set_name">Set Name</button>
                    </div>
                </div>
                <div id="add-card-section" style="display: none;">
                    <h3>Add New Card</h3>
                    <form method="post" id="add-form" class="card-form">
                        Cert Number: <input type="text" name="cert_number" id="cert_number_input">
                        <button type="submit">Add Card</button>
                    </form>
                </div>
                <div id="card-collection-grid" class="card-grid">
                    <p>Loading collection...</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    logged_in_user = session.get('username')
    # If a user is logged in, redirect them to their collection page
    if logged_in_user:
        return redirect(url_for('user_collection', username=logged_in_user))
    
    # If no one is logged in, show the login/register page directly
    return render_template_string(
        TEMPLATE, 
        logged_in_user=None, # Explicitly pass None
        current_displayed_user=None # Explicitly pass None
    )

@app.route("/login", methods=["POST"])
def login():
    username = request.form['username']
    password = request.form['password']
    
    users = load_json_file(USERS_FILE)
    if username in users and users[username]['password_hash'] == hash_password(password):
        session['username'] = username
        return jsonify({"message": "Login successful!", "username": username}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route("/register", methods=["POST"])
def register():
    username = request.form['username']
    password = request.form['password']

    users = load_json_file(USERS_FILE)
    if username in users:
        return jsonify({"error": "Username already exists"}), 409
    
    users[username] = {'password_hash': hash_password(password)}
    save_json_file(users, USERS_FILE)

    # Initialize an empty collection for the new user
    collections = load_json_file(COLLECTIONS_FILE)
    collections[username] = []
    save_json_file(collections, COLLECTIONS_FILE)

    session['username'] = username
    return jsonify({"message": "Registration successful!", "username": username}), 201

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/collection/<username>")
def user_collection(username):
    logged_in_user = session.get('username')
    return render_template_string(
        TEMPLATE, 
        logged_in_user=logged_in_user,
        current_displayed_user=username # This user's collection is being displayed
    )

@app.route("/add_card", methods=["POST"])
def add_card():
    logged_in_user = session.get('username')
    if not logged_in_user:
        return jsonify({"error": "Not logged in"}), 401

    cert_number = request.form["cert_number"].strip()
    card_info = scrape_card_info(cert_number)

    if "error" in card_info:
        return jsonify({"error": card_info["error"]}), 400
    
    collections = load_json_file(COLLECTIONS_FILE)
    # Ensure the user has a collection initialized
    if logged_in_user not in collections:
        collections[logged_in_user] = []

    # Assign a unique ID to the card for easier removal later
    # This is a simple timestamp-based ID; for high concurrency, use UUIDs
    card_info['id'] = str(time.time()).replace('.', '') 
    collections[logged_in_user].append(card_info)
    save_json_file(collections, COLLECTIONS_FILE)

    return jsonify({"message": "Card added successfully!"}), 200

@app.route("/remove_card", methods=["POST"])
def remove_card():
    logged_in_user = session.get('username')
    if not logged_in_user:
        return jsonify({"error": "Not logged in"}), 401

    cert_number_to_remove = request.form["cert_number"].strip()
    
    collections = load_json_file(COLLECTIONS_FILE)
    
    if logged_in_user in collections:
        original_count = len(collections[logged_in_user])
        collections[logged_in_user] = [
            card for card in collections[logged_in_user] 
            if card.get('cert_number') != cert_number_to_remove
        ]
        if len(collections[logged_in_user]) < original_count:
            save_json_file(collections, COLLECTIONS_FILE)
            return jsonify({"message": "Card removed successfully!"}), 200
        else:
            return jsonify({"error": "Card not found in your collection"}), 404
    else:
        return jsonify({"error": "Your collection does not exist"}), 404

@app.route("/get_all_users")
def get_all_users():
    users_data = load_json_file(USERS_FILE)
    user_list = list(users_data.keys()) # Get all usernames
    return jsonify({"users": user_list}), 200

@app.route("/get_user_collection/<username>")
def get_user_collection(username):
    collections = load_json_file(COLLECTIONS_FILE)
    cards = collections.get(username, [])
    return jsonify({"cards": cards}), 200

if __name__ == "__main__":
    app.run(debug=True)

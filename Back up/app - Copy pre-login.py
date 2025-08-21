from flask import Flask, render_template_string, request, redirect, url_for

import requests

from bs4 import BeautifulSoup

from selenium import webdriver

from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.service import Service

from webdriver_manager.chrome import ChromeDriverManager

import time



app = Flask(__name__)



# Store cards in memory for now

collection = []



TEMPLATE = """

<!DOCTYPE html>

<html>

<head>

    <title>Card Collection</title>

    <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap" rel="stylesheet">

    <style>

        body { 

            font-family: 'Open Sans', sans-serif; 

            margin: 20px; 

            background-color: black; 

            color: white; 

            font-size: 75%;

        }

        .card { 

            border: 1px solid #ccc; 

            padding: 10px; 

            margin: 10px;

            display: inline-block; 

            vertical-align: top; 

            width: 225px;

            min-height: 450px; /* Ensures consistent container height */

        }

        img { 

            display: block;

            margin: 0 auto;

            max-width: 100%;

        }

        button { 

            margin-top: 10px; 

        }

        .card p {

            margin: 0;

        }

        /* Ensure links and text within the card are visible */

        .card p, .card strong {

            color: white;

        }

        .card a {

            color: #88c0d0;

        }

    </style>

</head>

<body>

    <h1>My Card Collection</h1>

    <form method="post" action="/add">

        Cert Number: <input type="text" name="cert_number">

        <button type="submit">Add Card</button>

    </form>

    

    <div>

    {% for card in collection %}

        <div class="card">

            <img src="{{ card.image }}" alt="Card image">

            {% if card.line1 %}

            <p><strong>{{ card.line1 }}</strong></p>

            {% endif %}

            {% if card.line2 %}

            <p>{{ card.line2 }}</p>

            {% endif %}

            {% if card.line_subset %}

            <p>{{ card.line_subset }}</p>

            {% endif %}

            {% if card.line3 %}

            <p>{{ card.line3 }}</p>

            {% endif %}

            {% if card.line4 %}

            <p>{{ card.line4 }}</p>

            {% endif %}

            <p><a href="{{ card.link }}" target="_blank">{{ card.cert_number }}</a></p>

            <form method="post" action="/remove">

                <input type="hidden" name="cert_number" value="{{ card.cert_number }}">

                <button type="submit">Remove</button>

            </form>

        </div>

    {% endfor %}

    </div>

</body>

</html>

"""



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



        # Initialize all lines to an empty string

        line1, line2, line_subset, line3, line4 = "", "", "", "", ""

        

        # --- Line 1: Player name ---

        try:

            player_label = soup.find("span", string="Player name:")

            if player_label and player_label.find_next_sibling("span"):

                line1 = player_label.find_next_sibling("span").get_text(strip=True)

        except Exception:

            pass



        # --- Line 2: Set name ---

        try:

            set_name_label = soup.find("span", string="Set name:")

            if set_name_label and set_name_label.parent:

                set_name_full_text = set_name_label.parent.get_text(strip=True)

                line2 = set_name_full_text.replace("Set name:", "").strip()

        except Exception:

            pass

        

        # --- New line: Subset ---

        try:

            subset_label = soup.find("span", string="Subset:")

            if subset_label and subset_label.parent:

                subset_full_text = subset_label.parent.get_text(strip=True)

                line_subset = subset_full_text.replace("Subset:", "").strip()

                # Check for and remove hyphens

                if line_subset == "-":

                    line_subset = ""

        except Exception:

            pass



        # --- Line 3: Variation ---

        try:

            variation_label = soup.find("span", string="Variation:")

            if variation_label and variation_label.parent:

                variation_full_text = variation_label.parent.get_text(strip=True)

                line3 = variation_full_text.replace("Variation:", "").strip()

                # If the line contains only a hyphen, make it an empty string

                if line3 == "-":

                    line3 = ""

        except Exception:

            pass



        # --- Line 4: Grade ---

        try:

            # Attempt 1: Find using "View Score" anchor

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

            

            # Attempt 2: If "View Score" not found, try "TAG Score" anchor

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

            "cert_number": cert_number,

            "line1": "",

            "line2": "",

            "line_subset": "",

            "line3": "",

            "line4": "",

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



# Example usage:

cert_number = "W1200368"

card_info = scrape_card_info(cert_number)

print(card_info)



@app.route("/")

def index():

    return render_template_string(TEMPLATE, collection=collection)



@app.route("/add", methods=["POST"])

def add():

    cert_number = request.form["cert_number"].strip()

    card_info = scrape_card_info(cert_number)

    collection.append(card_info)

    return redirect(url_for("index"))



@app.route("/remove", methods=["POST"])

def remove():

    cert_number = request.form["cert_number"].strip()

    global collection

    collection = [c for c in collection if c["cert_number"] != cert_number]

    return redirect(url_for("index"))



if __name__ == "__main__":

    app.run(debug=True)
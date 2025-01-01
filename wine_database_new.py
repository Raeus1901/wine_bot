#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wine_database_new.py

Scrapes wine data from Vivino URLs and saves it to a CSV file.
"""

import re
import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.safari.service import Service as SafariService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import logging

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CSV_PATH = "/Users/jean/Documents/EAGLES/wine_chat/enriched_wine_data_safari.csv"

# -----------------------------------------------------------------------------
# Setup Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wine_scraper.log"),
        logging.StreamHandler()
    ]
)

# -----------------------------------------------------------------------------
# 1. SET UP SAFARI WEBDRIVER
# -----------------------------------------------------------------------------
def setup_driver():
    try:
        service = SafariService("/usr/bin/safaridriver")
        options = webdriver.SafariOptions()
        options.add_argument("--disable-gpu")
        driver = webdriver.Safari(service=service, options=options)
        logging.info("Safari WebDriver initialized successfully.")
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize Safari WebDriver: {e}")
        raise

driver = setup_driver()

# -----------------------------------------------------------------------------
# 2. WINE URLS (MERGED LIST)
# -----------------------------------------------------------------------------
wine_urls = [
    "https://test.psychologies.com/tests-qi/tests-psychotechniques/test-de-logique-visuelle/votre-resultat-exceptionnel",
    "https://www.vivino.com/explore?e=eJwtxksKwjAUBdDd3KH0I9XJnbkDcSSltC8pBJM25EVrd6-Qjs4xkfPo1SIktqcrgltYVwjjl5cKwsf9hsimw0eINRkaq4J12jlZzUN08lJsXN7eY8vPnnWhKbSFM2TXvy4fmdMRqz_c_iuW",
    "https://www.vivino.com/US/en/fabio-cordella-oscar-copertino-rosso/w/2600932?year=2020&price_id=36768448",
    "https://www.vivino.com/US/en/colcombet-freres-reserve-privee-brut-eclat-champagne/w/5074155?price_id=30176983",
    "https://www.vivino.com/US/en/chateau-boyd-cantenac-josephine-de-boyd-margaux/w/1206188?year=2015&price_id=26687142",
    "https://www.vivino.com/US/en/juan-gil-jumilla-blue-label/w/1713612?year=2022&price_id=37667741",
    "https://www.vivino.com/US/en/chateau-de-malle-m-de-malle-graves-blanc/w/90100?year=2015&price_id=35072711",
    "https://www.vivino.com/US/en/bodegas-marques-de-caceres-gaudium/w/2076733?year=2019&price_id=36096731",
    "https://www.vivino.com/US/en/atalaya-almansa-alaya-tierra-almansa/w/3772025?year=2021&price_id=35113165",
    "https://www.vivino.com/US/en/chateau-de-lou-22586-grenache-rhapsody/w/6970989?year=2019&price_id=29462589",
    "https://www.vivino.com/US/en/ferragu-valpolicella-superiore/w/1171438?year=2019&price_id=35556473",
    "https://www.vivino.com/US/en/terre-du-lion-saint-julien/w/1294863?year=2020&price_id=36316612",
    "https://www.vivino.com/US/en/aldi-fuga-cabernet-puglia/w/11003461?year=2021&price_id=33573579",
    "https://www.vivino.com/US/en/la-giaretta-amarone-della-valpolicella-classico/w/91908?year=2020&price_id=34790319",
    "https://www.vivino.com/US/en/cellier-des-princes-heredita-chateauneuf-du-pape/w/7124268?year=2019&price_id=36188775",
    "https://www.vivino.com/US/en/nic-tartaglia-bifolco-cabernet/w/6906754?year=2016&price_id=33354309",
    "https://www.vivino.com/US/en/chateau-de-respide-callipyge-graves-blanc/w/2064553?year=2021&price_id=32966093",
    # Add the remaining URLs here
]


# -----------------------------------------------------------------------------
# 3. CSV COLUMNS
# -----------------------------------------------------------------------------
columns = [
    "Alcohol Level (ABV)", 
    "Winery", 
    "Name", 
    "Vintage", 
    "Country", 
    "Region", 
    "Colour of Wine", 
    "Blend", 
    "Grape Types", 
    "Ratings", 
    "Number of Ratings",
    "Price",
    "Body (Light-Bold)", 
    "Tannins (Smooth-Tannic)", 
    "Sweetness (Dry-Sweet)", 
    "Acidity (Soft-Acidic)",
    "Description",
    "Flavor Notes", 
    "Food Pairings",
    "Wine Tastes"
]

# Initialize a container for data
data = []

# Set up an explicit wait for Safari (10 seconds)
wait = WebDriverWait(driver, 10)

# -----------------------------------------------------------------------------
# Helper function to parse taste profiles
# -----------------------------------------------------------------------------
def parse_taste_profile(soup_obj, property_name):
    """
    Look for the row labeled with property_name (e.g., "Light", "Smooth", etc.)
    and parse the width% out of the progress bar. Returns an integer or None.
    """
    try:
        # Use 'string' instead of 'text'
        row = soup_obj.find('div', string=property_name)
        if not row:
            row = soup_obj.find('td', string=property_name)
        if row:
            # Access the parent row and find the 'span' with style
            progress_bar = row.find_parent('tr').find('span', class_='indicatorBar__progress--3aXLX')
            if progress_bar and 'style' in progress_bar.attrs:
                style = progress_bar['style']
                match = re.search(r'width:\s*(\d+)%', style)
                if match:
                    return int(match.group(1))
        return None
    except Exception as e:
        logging.error(f"Error parsing taste profile '{property_name}': {e}")
        return None

# -----------------------------------------------------------------------------
# MAIN SCRAPING LOOP
# -----------------------------------------------------------------------------
for idx, url in enumerate(wine_urls, start=1):
    try:
        logging.info(f"Scraping URL {idx}/{len(wine_urls)}: {url}")
        driver.get(url)

        # Click 'More' button if present (to reveal full description)
        try:
            more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".collapse__toggle")))
            more_button.click()
            # Optional short sleep to let page expand
            time.sleep(1)
            logging.info("Clicked 'More' button.")
        except Exception:
            logging.info("No 'More' button found or unable to click it.")

        # Wait for rating element to ensure page content loads
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".vivinoRating_averageValue__uDdPM")))
            logging.info("Rating element found.")
        except Exception:
            logging.warning("Rating element not found.")

        # Parse the final HTML
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        # -----------
        # Extract ABV
        # -----------
        abv = None
        try:
            # Method 1: Look for "Alcohol content" label
            alcohol_header = soup.find('span', {'class': 'wineFacts__headerLabel--14doB'}, string="Alcohol content")
            if alcohol_header:
                abv_cell = alcohol_header.find_parent('th').find_next_sibling('td')
                if abv_cell:
                    abv_value = abv_cell.get_text(strip=True).replace("%", "")
                    abv = float(abv_value) if abv_value else None
            else:
                # Method 2: Fallback -> find a span with something% in text
                abv_span = soup.find('span', string=re.compile(r'\d+%'))
                if abv_span:
                    abv_value = abv_span.get_text(strip=True).replace("%", "")
                    abv = float(abv_value) if abv_value else None
        except Exception as e:
            abv = None
            logging.error(f"Error extracting ABV: {e}")

        # -----------
        # Winery
        # -----------
        winery = None
        try:
            # Attempt: some Vivino pages place winery in multiple spots
            # 1) Check class = 'winery'
            winery_elem = soup.find('a', {'class': 'winery', 'data-cartitemsource': 'winery-page-wine-page-header'})
            if winery_elem:
                winery = winery_elem.get_text(strip=True)
            else:
                # Fallback approach
                winery_elem2 = soup.find('span', {'data-cy': 'wine-page-winery'})
                if winery_elem2:
                    winery = winery_elem2.get_text(strip=True)
            if not winery:
                winery = "Unknown Winery"
        except Exception as e:
            winery = "Unknown Winery"
            logging.error(f"Error extracting Winery: {e}")

        # -----------
        # Wine Name
        # -----------
        name = None
        try:
            # Usually inside <a class='wine' data-cartitemsource='wine-page-master-link'>
            name_elem = soup.find('a', {'class': 'wine', 'data-cartitemsource': 'wine-page-master-link'})
            if name_elem:
                name = name_elem.get_text(strip=True)
            else:
                # Fallback, check h1 or so
                name_h1 = soup.find('h1', {'class': 'summary'})
                if name_h1:
                    name = name_h1.get_text(strip=True)
            if not name:
                name = "Unknown Wine Name"
        except Exception as e:
            name = "Unknown Wine Name"
            logging.error(f"Error extracting Wine Name: {e}")

        # -----------
        # Vintage
        # -----------
        vintage = None
        try:
            # Typically inside <span class='vintage'>
            vintage_parent = soup.find('span', {'class': 'vintage'})
            if vintage_parent:
                vintage_text = vintage_parent.get_text(strip=True)
                # Regex to capture 19xx or 20xx
                found = re.search(r'(19[5-9]\d|20[0-4]\d)', vintage_text)
                if found:
                    vintage = found.group(0)
            if not vintage:
                vintage = "Unknown Vintage"
        except Exception as e:
            vintage = "Unknown Vintage"
            logging.error(f"Error extracting Vintage: {e}")

        # -----------
        # Country
        # -----------
        country = None
        try:
            country_elem = soup.find('a', {'data-cy': 'breadcrumb-country'})
            if country_elem:
                country = country_elem.get_text(strip=True)
            else:
                country = "Unknown Country"
        except Exception as e:
            country = "Unknown Country"
            logging.error(f"Error extracting Country: {e}")

        # -----------
        # Region
        # -----------
        region = None
        try:
            region_elem = soup.find('a', {'data-cy': 'breadcrumb-region'})
            if region_elem:
                region = region_elem.get_text(strip=True)
            else:
                region = "Unknown Region"
        except Exception as e:
            region = "Unknown Region"
            logging.error(f"Error extracting Region: {e}")

        # -----------
        # Colour of Wine
        # -----------
        colour_of_wine = None
        try:
            colour_elem = soup.find('a', {'data-cy': 'breadcrumb-winetype'})
            if colour_elem:
                colour_of_wine = colour_elem.get_text(strip=True)
            else:
                colour_of_wine = "Unknown Colour"
        except Exception as e:
            colour_of_wine = "Unknown Colour"
            logging.error(f"Error extracting Colour of Wine: {e}")

        # -----------
        # Blend
        # -----------
        blend = None
        try:
            blend_elem = soup.find('a', {'data-cy': 'breadcrumb-grape'})
            if blend_elem:
                blend = blend_elem.get_text(strip=True)
            else:
                blend = "Single Variety"
        except Exception as e:
            blend = "Single Variety"
            logging.error(f"Error extracting Blend: {e}")

        # -----------
        # Grape Types
        # -----------
        grape_types_str = None
        try:
            grape_types_elems = soup.find_all('a', {'class': 'wineFacts__link--3aTg9', 'href': re.compile(r'/grapes/')})
            grape_types = [gt.get_text(strip=True) for gt in grape_types_elems]
            if grape_types:
                grape_types_str = ", ".join(grape_types)
            else:
                grape_types_str = "Unknown Grape Types"
        except Exception as e:
            grape_types_str = "Unknown Grape Types"
            logging.error(f"Error extracting Grape Types: {e}")

        # -----------
        # Ratings (average rating)
        # -----------
        ratings = None
        try:
            rating_element = soup.find('div', {'class': 'vivinoRating_averageValue__uDdPM'})
            if rating_element:
                ratings = float(rating_element.get_text(strip=True))
            else:
                ratings = 0.0  # Default rating if not found
        except Exception as e:
            ratings = 0.0
            logging.error(f"Error extracting Ratings: {e}")

        # -----------
        # Number of Ratings
        # -----------
        num_ratings = None
        try:
            num_ratings_element = soup.find('div', {'class': 'vivinoRating_caption__xL84P'})
            if num_ratings_element:
                num_ratings_text = num_ratings_element.get_text(strip=True)
                num_ratings_match = re.search(r'(\d[\d,\.]*)', num_ratings_text)
                if num_ratings_match:
                    # Remove commas and convert to integer
                    num_ratings = int(num_ratings_match.group(1).replace(",", ""))
            if num_ratings is None:
                num_ratings = 0  # Default if not found
        except Exception as e:
            num_ratings = 0
            logging.error(f"Error extracting Number of Ratings: {e}")

        # -----------
        # Price
        # -----------
        price = None
        try:
            price_elem = soup.find('span', {'class': 'purchaseAvailability__currentPrice--3mO4u'})
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Remove $ or € or commas
                price_text = price_text.replace("$", "").replace("€", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    price = 0.0  # Default if conversion fails
            else:
                price = 0.0  # Default if not found
        except Exception as e:
            price = 0.0
            logging.error(f"Error extracting Price: {e}")

        # -----------
        # Taste Profiles
        # -----------
        light_bold = parse_taste_profile(soup, "Light")
        smooth_tannic = parse_taste_profile(soup, "Smooth")
        dry_sweet = parse_taste_profile(soup, "Dry")
        soft_acidic = parse_taste_profile(soup, "Soft")

        # -----------
        # Description
        # -----------
        description = None
        try:
            description_element = soup.find('div', {'class': 'fullEditorNote__note--RdYag'})
            if description_element:
                description = description_element.get_text(strip=True)
            else:
                description = "No Description Available"
        except Exception as e:
            description = "No Description Available"
            logging.error(f"Error extracting Description: {e}")

        # -----------
        # Flavor Notes
        # -----------
        flavor_notes_str = None
        try:
            flavor_notes = []
            flavor_elements = soup.find_all('button', {'class': 'tasteNote__tasteNote--wtLz7'})
            for fe in flavor_elements:
                keywords_elem = fe.find('div', {'class': 'tasteNote__popularKeywords--1gIa2'})
                mentions_elem = fe.find('div', {'class': 'tasteNote__mentions--1T_d5'})
                if keywords_elem and mentions_elem:
                    keywords = keywords_elem.get_text(strip=True)
                    mentions = mentions_elem.get_text(strip=True)
                    flavor_notes.append(f"{keywords} | {mentions}")
            if flavor_notes:
                flavor_notes_str = "; ".join(flavor_notes)
            else:
                flavor_notes_str = "No Flavor Notes"
        except Exception as e:
            flavor_notes_str = "No Flavor Notes"
            logging.error(f"Error extracting Flavor Notes: {e}")

        # -----------
        # Food Pairings
        # -----------
        food_pairings = None
        try:
            food_parent = soup.find('div', {'class': 'food-pairing__list'})
            if food_parent:
                foods = [f.get_text(strip=True) for f in food_parent.find_all('li', {'class': 'food-pairing__item'})]
                food_pairings = ", ".join(foods)
            else:
                # Fallback
                food_pairings = "Beef, Veal, Poultry, Game"
        except Exception as e:
            food_pairings = "Beef, Veal, Poultry, Game"
            logging.error(f"Error extracting Food Pairings: {e}")

        # -----------
        # Wine Tastes
        # -----------
        wine_tastes_str = None
        try:
            wine_tastes = []
            taste_elements = soup.find_all('button', {'class': 'tasteNote__tasteNote--wtLz7'})
            for te in taste_elements:
                popular_keywords = te.find('div', {'class': 'tasteNote__popularKeywords--1gIa2'})
                mentions_elem = te.find('div', {'class': 'tasteNote__mentions--1T_d5'})
                if popular_keywords and mentions_elem:
                    keywords = popular_keywords.get_text(strip=True)
                    mentions = mentions_elem.get_text(strip=True)
                    wine_tastes.append(f"{keywords} | {mentions}")
            if wine_tastes:
                wine_tastes_str = "; ".join(wine_tastes)
            else:
                wine_tastes_str = "No Wine Tastes"
        except Exception as e:
            wine_tastes_str = "No Wine Tastes"
            logging.error(f"Error extracting Wine Tastes: {e}")

        # ---------------------------------------------------------------------
        # Append row to data
        # ---------------------------------------------------------------------
        data.append([
            abv, 
            winery, 
            name, 
            vintage, 
            country, 
            region, 
            colour_of_wine, 
            blend, 
            grape_types_str, 
            ratings, 
            num_ratings,
            price,
            light_bold, 
            smooth_tannic, 
            dry_sweet, 
            soft_acidic,
            description,
            flavor_notes_str, 
            food_pairings,
            wine_tastes_str
        ])

        logging.info(f"Finished scraping URL {idx}/{len(wine_urls)}.\n")

    except Exception as e:
        logging.error(f"An error occurred while processing URL {url}: {e}")
        # Skip to the next URL
        continue

# -----------------------------------------------------------------------------
# 4. CLOSE THE BROWSER
# -----------------------------------------------------------------------------
driver.quit()
logging.info("Closed Safari WebDriver.")

# -----------------------------------------------------------------------------
# 5. SAVE / MERGE DATAFRAME TO CSV
# -----------------------------------------------------------------------------
df_new = pd.DataFrame(data, columns=columns)

try:
    if os.path.isfile(CSV_PATH):
        # Load existing CSV
        df_old = pd.read_csv(CSV_PATH, encoding='utf-8', quoting=csv.QUOTE_ALL)
        logging.info(f"Loaded existing CSV with {len(df_old)} rows.")
        # Merge new data
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        logging.info(f"Combined data has {len(df_combined)} rows.")
        # Drop duplicates based on ['Name', 'Vintage', 'Country']
        df_combined.drop_duplicates(subset=["Name", "Vintage", "Country"], keep="last", inplace=True)
        logging.info(f"After dropping duplicates, {len(df_combined)} rows remain.")
        # Save combined CSV with proper quoting
        df_combined.to_csv(
            CSV_PATH, 
            index=False, 
            encoding='utf-8', 
            quoting=csv.QUOTE_ALL
        )
        logging.info(f"Updated CSV saved to '{CSV_PATH}'.")
    else:
        # Create new CSV with proper quoting
        df_new.to_csv(
            CSV_PATH, 
            index=False, 
            encoding='utf-8', 
            quoting=csv.QUOTE_ALL
        )
        logging.info(f"Created new CSV with {len(df_new)} rows at '{CSV_PATH}'.")
except Exception as e:
    logging.error(f"Error merging or saving CSV: {e}")

logging.info("Data scraping completed. Check 'enriched_wine_data_safari.csv' for the results.")

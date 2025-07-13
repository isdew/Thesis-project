# 025-04-07 21:06:20,973 - INFO - 📍 Scraping 706/1355: https://www.facebook.com/marketplace/item/1208345477129593/
# 2025-04-07 21:06:29,274 - INFO - 📌 Title: พาวเวอร์แบงค์ดูดแม่เหล็กไร้สาย 10000mah
# 2025-04-07 21:06:29,460 - WARNING - ⚠ No matching images found.
# 2025-04-07 21:06:29,461 - ERROR - ❌ Failed to scrape https://www.facebook.com/marketplace/item/1208345477129593/: cannot access local variable 'alt_clean' where it is not associated with a value

import os
import time
import random
import csv
import re
import unicodedata
import logging
import requests
import shutil
import wget
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from ultralytics import YOLO

# Load YOLOv11 model (replace with your correct path)
TIS_model = YOLO(r"C:\Users\patza\Desktop\Capstone_Project\Project\YoloV11\runs\detect\train9\weights\best.pt")


# ------------------------ CONFIG ------------------------
KEYWORDS = [
    "Power bank", "พาวเวอร์แบงค์", "PowerBank", "แบตสำรอง",
    "powerbank", "eloop", "แบตเตอรี่สำรอง", "เพาเวอร์แบงก์", "พาวเวอร์เเบง"
]
#["Power bank", "พาวเวอร์แบงค์", "PowerBank", "แบตสำรอง","powerbank", "eloop", "แบตเตอรี่สำรอง"]
FILTER_KEYWORDS = [
    "Power bank", "พาวเวอร์แบงค์", "PowerBank", "แบตสำรอง",
    "powerbank", "แบตเตอรี่สำรอง", "เพาเวอร์แบงก์", "พาวเวอร์เเบง", "power bank",
    "พาวเวอเเบงค์", "เพาเวอร์แบงค์"
]
#k.lower() for k in KEYWORDS

download_images = True  # Toggle this to True to download images
CSV_FILE = "New_Scaping/marketplace_data.csv"
SKIPPED_CSV = "New_Scaping/skipped_posts.csv"
IMAGE_DIR = "New_Scaping/images"
SCROLL_LIMIT = 15
ZOOM_LEVEL = 0.5
PROFILE_PATH = r"C:\\Users\\patza\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_NAME = "Profile 8"
CHROMEDRIVER_PATH = r"C:\\Users\\patza\\chromedriver.exe"

# ------------------------ SETUP ------------------------
def setup_chrome():
    os.system("taskkill /im chrome.exe /f") 
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument(f"--profile-directory={PROFILE_NAME}")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--force-device-scale-factor=" + str(ZOOM_LEVEL))
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("detach", True)

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    driver.get("https://www.facebook.com")
    return driver

# ------------------------ HELPERS ------------------------
def detect_tis_symbol(image_path):
    results = TIS_model.predict(image_path, conf=0.5)  # Confidence threshold adjust if needed
    detections = results[0].boxes.xyxy  # Bounding boxes format (x1, y1, x2, y2)
    
    if len(detections) > 0:
        logging.info(f"🎯 TIS symbol detected in {image_path}")
        return True
    else:
        logging.info(f"❌ No TIS symbol detected in {image_path}")
        return False

def save_csv_row(filename, row, header=None):
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists and header:
            writer.writerow(header)
        writer.writerow(row)

def normalize_text(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF\uFFFC\uFFFD]", '', text)
    text = re.sub(r"\s+", ' ', text)
    return text.lower().strip()

def sanitize_filename(title):
    return re.sub(r'[<>:"/\\|?*]', '_', title)

# ------------------------ MAIN SCRAPER ------------------------
def search_facebook(driver, query):
    driver.get("https://www.facebook.com/marketplace")
    time.sleep(5)

    search_box = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search Marketplace']"))
    )
    search_box.send_keys(query + "\n")
    time.sleep(7)

    links = set()
    skipped = set()

    for scroll in range(SCROLL_LIMIT):
        logging.info(f"🔄 Scroll {scroll + 1}/{SCROLL_LIMIT}")
        time.sleep(8)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.find_all("a", href=True)

        for item in items:
            href = item["href"]
            if "/marketplace/item/" not in href:
                continue

            link = f"https://www.facebook.com{href.split('?')[0]}"
            title_elem = item.find("span", class_="x1lliihq x6ikm8r x10wlt62 x1n2onr6")
            title = title_elem.text.strip().lower() if title_elem else ""

            if title and not any(k in title for k in FILTER_KEYWORDS):
                skipped.add((title, link))
                continue
            links.add(link)

        driver.execute_script("window.scrollBy(0, 1950);")

    for skip in skipped:
        save_csv_row(SKIPPED_CSV, list(skip))

    logging.info(f"📊 Found: {len(links)} links, Skipped: {len(skipped)}")
    return links, skipped

def scrape_post(driver, post_url):
    driver.get(post_url)
    time.sleep(3)

    try:
        title_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span["
                "contains(@class, 'x193iq5w') and contains(@class, 'xeuugli') and contains(@class, 'x13faqbe') and "
                "contains(@class, 'x1vvkbs') and contains(@class, 'x1xmvt09') and contains(@class, 'x1lliihq') and "
                "contains(@class, 'x1s928wv') and contains(@class, 'xhkezso') and contains(@class, 'x1gmr53x') and "
                "contains(@class, 'x1cpjm7i') and contains(@class, 'x1fgarty') and contains(@class, 'x1943h6x') and "
                "contains(@class, 'x14z4hjw') and contains(@class, 'x3x7a5m') and contains(@class, 'xngnso2') and "
                "contains(@class, 'x1qb5hxa') and contains(@class, 'x1xlr1w8') and contains(@class, 'xzsf02u') and "
                "not(contains(@class, 'x1yc453h'))]"))
        )
        title = title_elem.text.strip()
        logging.info(f"📌 Title: {title}")
    except:
        logging.warning("⚠ Title not found.")
        return

    safe_title = sanitize_filename(title)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    img_elements = driver.find_elements(By.XPATH,
        "//div[contains(@class, 'x1ypdohk') and contains(@class, 'xc9qbxq') and contains(@class, 'x14qfxbe') and "
        "contains(@class, 'xti2d7y') and contains(@class, 'x5z6fxw')]"
        "//img[contains(@class, 'x1o1ewxj') and contains(@class, 'x3x9cwd') and contains(@class, 'x1e5q0jg') and "
        "contains(@class, 'x13rtm0m') and contains(@class, 'x5yr21d') and contains(@class, 'xl1xv1r') and "
        "contains(@class, 'xh8yej3')]"
        " | "
        "//span[@aria-hidden='true' and contains(@class, 'x78zum5') and contains(@class, 'x1vjfegm')]"
        "//img[contains(@class, 'xz74otr') and contains(@class, 'x168nmei') and contains(@class, 'x13lgxp2') and "
        "contains(@class, 'x5pf9jr') and contains(@class, 'xo71vjh')]"
    )

    matched_urls = []
    tis_detection_results = []

    for img in img_elements:
        url = img.get_attribute("src")
        if url:
            matched_urls.append(url)
            logging.info(f"✅ Collected Image URL: {url}")
            
            # 🔵 Always temporary download for detection
            temp_filename = os.path.join(IMAGE_DIR, f"temp_{int(time.time())}.jpg")
            wget.download(url, temp_filename, bar=None)  # Turn off progress bar for speed
            
            # 🛠 Detect TIS symbol
            tis_found = detect_tis_symbol(temp_filename)
            tis_detection_results.append(tis_found)
            
            # 📦 If user wants to save images permanently
            if download_images:
                permanent_filename = os.path.join(IMAGE_DIR, f"{sanitize_filename(title)}_{int(time.time())}.jpg")
                shutil.move(temp_filename, permanent_filename)
                logging.info(f"📸 Saved permanent image: {permanent_filename}")
            else:
                os.remove(temp_filename)
                logging.info(f"🗑️ Deleted temporary file: {temp_filename}")
            
            time.sleep(random.uniform(1, 2))


    # Determine overall TIS presence for the post (at least one image has TIS)
    tis_detected = any(tis_detection_results)

    if matched_urls:
        row = [title, post_url, " | ".join(matched_urls), "Yes" if tis_detected else "No"]
        save_csv_row(CSV_FILE, row, header=["Title", "Post Link", "Photo Link", "TIS Detected"])
        logging.info(f"✅ Saved to CSV: {title} (TIS Detected: {'Yes' if tis_detected else 'No'})")
    else:
        logging.warning("⚠ No images found.")


# ------------------------ RUN ------------------------
if __name__ == "__main__":
    logging.basicConfig( #--------- LOGGER SETUP ------
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("New_Scaping/scraper_log.txt", mode='w', encoding="utf-8"),
            logging.StreamHandler()  # Console output
        ]
    )

    driver = setup_chrome()
    os.makedirs(IMAGE_DIR, exist_ok=True)

    all_links = set()
    all_skipped = set()
    keyword_summary = defaultdict(lambda: {'found': 0, 'skipped': 0})

    for keyword in KEYWORDS:
        found, skipped = search_facebook(driver, keyword)
        all_links.update(found)
        all_skipped.update(skipped)
        keyword_summary[keyword]['found'] = len(found)
        keyword_summary[keyword]['skipped'] = len(skipped)

    print("\n====================== FINAL SUMMARY ======================")
    total_found = total_skipped = 0 #Still got duplicate between run
    for keyword, counts in keyword_summary.items():
        found = counts['found']
        skipped = counts['skipped']
        total_found += found
        total_skipped += skipped
        logging.info(f"🔍 Keyword: {keyword}")
        logging.info(f"   ✅ Total Post Links Found: {found + skipped}")
        logging.info(f"   📌 Total Unique Post Links Collected: {found}")
        logging.info(f"   ❌ Total Skipped Post Links Collected: {skipped}\n")

    logging.info("📊 Overall Summary:")
    logging.info(f"   ✅ Total Post Links Found (exclude duplicate): {len(all_links) + len(all_skipped)}")
    logging.info(f"   📌 Total Unique Post Links Collected (exclude duplicate): {len(all_links)}")
    logging.info(f"   ❌ Total Skipped Post Links Collected (exclude duplicate): {len(all_skipped)}")
    logging.info("===========================================================\n")

    logging.info(f"✅ Total unique posts to scrape: {len(all_links)}")

    for idx, link in enumerate(all_links):
        logging.info(f"📍 Scraping {idx+1}/{len(all_links)}: {link}")
        try:
            scrape_post(driver, link)
        except Exception as e:
            logging.error(f"❌ Failed to scrape {link}: {e}")
        time.sleep(random.uniform(2, 4))


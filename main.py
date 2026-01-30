#branch: restructure-cleanup //Make a folder for overlay picture where locate TIS, QR. The downloading rn are duplicate x2, it download 2 times. direct picture with TIS and QR into itown folder for dataset and none too.
import os
import time
import random
import csv
import re
import unicodedata
import logging
import shutil
import wget
import hashlib
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from ultralytics import YOLO
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
import subprocess
from Module.product_config import ProductConfig

# Load YOLOv11 model (replace with your correct path)
TIS_model = YOLO(r"model\TIS.pt")
QR_model = YOLO(r"model\QR.pt")


# ------------------------ CONFIG ------------------------
# Load configuration
config = ProductConfig()

# Select product (this will come from frontend later)
SELECTED_PRODUCT = "power_bank"  # or "adapter", "usb_cable", etc.

# Get keywords dynamically
KEYWORDS = config.get_keywords(SELECTED_PRODUCT)
FILTER_KEYWORDS = config.get_filter_keywords(SELECTED_PRODUCT)
FILTER_KEYWORDS_LOWER = config.get_filter_keywords_lower(SELECTED_PRODUCT)

# Create product-specific output directories
PRODUCT_NAME = config.get_product_names()[SELECTED_PRODUCT]
CSV_FILE = f"Scrape_Data/{SELECTED_PRODUCT}/marketplace_data.csv"
SKIPPED_CSV = f"Scrape_Data/{SELECTED_PRODUCT}/skipped_posts.csv"
IMAGE_DIR = f"Scrape_Data/{SELECTED_PRODUCT}/images"

# ------------------------ PARAMETERS ------------------------

download_images = True  # Toggle this to True to download images
TIS_cf_threshold = 0.5  # Confidence threshold for TIS detection
QR_cf_threshold = 0.5  # Confidence threshold for QR detection /use auto-threshold for future run
CSV_FILE = "Scrape_Data/marketplace_data.csv"
SKIPPED_CSV = "Scrape_Data/skipped_posts.csv"
IMAGE_DIR = "Scrape_Data/images"
CATEGORY_ROOT = os.path.join(IMAGE_DIR, "categorized")  # Scrape_Data/  images/categorized
SCROLL_LIMIT = 2 #15
ZOOM_LEVEL = 0.5
PROFILE_PATH = r"C:\Users\patza\Desktop\Capstone_Project\profile"
PROFILE_NAME = "Profile 8"
CHROMEDRIVER_PATH = r"C:\\Users\\patza\\chromedriver.exe"

# ------------------------ SETUP ------------------------
def setup_chrome():
    # Try to close any running Chrome; ignore if not found
    try:
        subprocess.run(["taskkill", "/im", "chrome.exe", "/f"], check=False,
                       capture_output=True, text=True)
    except Exception:
        pass

    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_PATH}")
    opts.add_argument(f"--profile-directory={PROFILE_NAME}")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--force-device-scale-factor={ZOOM_LEVEL}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("detach", True)

    # No executable_path → Selenium Manager downloads the matching ChromeDriver 140
    service = Service()
    driver = Chrome(service=service, options=opts)
    driver.maximize_window()
    driver.get("https://www.facebook.com")
    return driver

# ------------------------ HELPERS ------------------------
def detect_tis_symbol(image_path):
    r = TIS_model.predict(image_path, conf=TIS_cf_threshold, verbose=False)[0]
    boxes = getattr(r, "boxes", None)
    found = boxes is not None and len(boxes) > 0
    logging.info(f"{'🎯' if found else '❌'} TIS symbol {'detected' if found else 'not detected'} in {image_path}")
    return found

def detect_qr_symbol(image_path):
    r = QR_model.predict(image_path, conf=QR_cf_threshold, verbose=False)[0]
    boxes = getattr(r, "boxes", None)
    found = boxes is not None and len(boxes) > 0
    logging.info(f"{'📷' if found else '❌'} QR code {'detected' if found else 'not detected'} in {image_path}")
    return found

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

def category_from_flags(tis_found: bool, qr_found: bool) -> str:
    """Two-bucket categorization."""
    return "has_mark" if (tis_found or qr_found) else "none"

# If you prefer 4 buckets, use this instead:
# def category_from_flags(tis_found: bool, qr_found: bool) -> str:
#     if tis_found and qr_found: return "both"
#     if tis_found: return "tis"
#     if qr_found:  return "qr"
#     return "none"

def archive_to_category(local_path: str, category_root: str, category: str) -> str:
    """
    Copy the saved image into a category folder.
    (Copy instead of move so the original master stays in IMAGE_DIR.)
    """
    dest_dir = os.path.join(category_root, category)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(local_path))
    if not os.path.exists(dest_path):
        shutil.copy2(local_path, dest_path)  # preserve timestamps/metadata
    return dest_path


# Global map so a URL is only downloaded once per run
URL_TO_FILE = {}  # {image_url: local_file_path}

def guess_ext_from_url(url: str) -> str:
    """
    Try to guess file extension from URL path; default to .jpg.
    """
    path = unquote(urlparse(url).path)
    ext = (path.split('.')[-1].lower() if '.' in path else '')
    if ext in {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"}:
        return "." + ("jpg" if ext == "jpeg" else ext)
    return ".jpg"

def filename_for_image(title: str, url: str) -> str:
    """
    Stable, de-duplicated filename using a hash of the URL + sanitized title.
    Prevents multiple downloads of identical URLs.
    """
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{sanitize_filename(title)}_{h}{guess_ext_from_url(url)}"

def ensure_download(url: str, title: str, image_dir: str) -> str:
    """
    Download url -> local file once. Reuse on subsequent requests.
    Returns local filepath.
    """
    # Reuse if downloaded already this run
    if url in URL_TO_FILE and os.path.exists(URL_TO_FILE[url]):
        return URL_TO_FILE[url]
    os.makedirs(image_dir, exist_ok=True)
    local_path = os.path.join(image_dir, filename_for_image(title, url))
    if not os.path.exists(local_path):
        try:
            wget.download(url, local_path, bar=None)
        except Exception as e:
            logging.warning(f"⚠ Download failed for {url}: {e}")
            raise
    URL_TO_FILE[url] = local_path
    return local_path
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
            title_elem = item.find("div", class_="xyqdw3p xyri2b xjkvuk6 x1c1uobl") #class_="x1lliihq x6ikm8r x10wlt62 x1n2onr6"
            raw_title = title_elem.get_text(strip=True) if title_elem else ""
            title_norm = normalize_text(raw_title)  # lower+normalize here
            if title_norm and not any(k in title_norm for k in FILTER_KEYWORDS_LOWER):
                skipped.add((title_norm, link))
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
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class,'xyamay9')"
                " and contains(@class,'xv54qhq')"
                " and contains(@class,'x18d9i69')"
                " and contains(@class,'xf7dkkf')]"
                "//span[@dir='auto']"
            ))
        )
        title = title_elem.text.strip()
        logging.info(f"📌 Title: {title}")
        # ---- reliable post-page title filter ----// for extra caution, if no need can remove later.
        title_norm = normalize_text(title)  # normalizes + lowercases
        if title_norm and not any(k in title_norm for k in FILTER_KEYWORDS_LOWER):
            logging.info(f"⏭️ Skipped by post-page filter: {title}")
            return

    except:
        logging.warning("⚠ Title not found.")
        return

    safe_title = sanitize_filename(title)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    img_elements = driver.find_elements(By.XPATH,
    # First path: span → img for post with single image
    "//span[contains(@class, 'x78zum5') and contains(@class, 'x1vjfegm')]"
    "//img[contains(@class, 'xz74otr') and contains(@class, 'x15mokao') and contains(@class, 'x1ga7v0g') and "
    "contains(@class, 'x16uus16') and contains(@class, 'xbiv7yw')]"
    " | "
    # Second path: standalone img for post with multiple images
    "//img[contains(@class, 'x1fmog5m') and contains(@class, 'xu25z0z') and contains(@class, 'x140muxe') and "
    "contains(@class, 'xo1y3bh') and contains(@class, 'x5yr21d') and contains(@class, 'xl1xv1r') and "
    "contains(@class, 'xh8yej3')]"
    )

    matched_urls = []
    tis_detection_results = []
    qr_detection_results = []
    seen_src = set()

    for img in img_elements:
        url = img.get_attribute("src")
        if not url or url in seen_src:
            continue
        seen_src.add(url)
        matched_urls.append(url)
        logging.info(f"✅ Collected Image URL: {url}")

        if download_images:
            # PERMANENT mode (data gathering) + categorization
            local_path = ensure_download(url, title, IMAGE_DIR)

            # detect
            try:
                tis = detect_tis_symbol(local_path)
            except Exception as e:
                logging.warning(f"⚠ TIS detection failed on {local_path}: {e}")
                tis = False
            try:
                qr = detect_qr_symbol(local_path)
            except Exception as e:
                logging.warning(f"⚠ QR detection failed on {local_path}: {e}")
                qr = False

            tis_detection_results.append(tis)
            qr_detection_results.append(qr)

            # categorize copy
            cat = category_from_flags(tis, qr)
            archived = archive_to_category(local_path, CATEGORY_ROOT, cat)
            logging.info(f"🗂️ Categorized -> {cat}: {archived}")


        else:
            # TEMP mode (production): download -> detect -> delete
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                tmp_path = tf.name
            try:
                wget.download(url, tmp_path, bar=None)
                try:
                    tis_detection_results.append(detect_tis_symbol(tmp_path))
                except Exception as e:
                    logging.warning(f"⚠ TIS detection failed on temp: {e}")
                    tis_detection_results.append(False)
                try:
                    qr_detection_results.append(detect_qr_symbol(tmp_path))
                except Exception as e:
                    logging.warning(f"⚠ QR detection failed on temp: {e}")
                    qr_detection_results.append(False)
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        time.sleep(random.uniform(0.4, 0.8))



    # Determine overall TIS presence for the post (at least one image has TIS)
    tis_detected = any(tis_detection_results)
    qr_detected = any(qr_detection_results)


    if matched_urls:
        row = [title, post_url, " | ".join(matched_urls), 
       "Yes" if tis_detected else "No", 
       "Yes" if qr_detected else "No"]
        save_csv_row(CSV_FILE, row, header=["Title", "Post Link", "Photo Link", "TIS Detected", "QR Detected"])

        logging.info(f"✅ Saved to CSV: {title} (TIS Detected: {'Yes' if tis_detected else 'No'})")
    else:
        logging.warning("⚠ No images found.")


# ------------------------ RUN ------------------------
if __name__ == "__main__":
    logging.basicConfig( #--------- LOGGER SETUP ------
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("Result/scraper_log.txt", mode='w', encoding="utf-8"),
            logging.StreamHandler()  # Console output
        ]
    )

    driver = setup_chrome()
    os.makedirs(IMAGE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(SKIPPED_CSV), exist_ok=True)
    os.makedirs(os.path.dirname("Result/scraper_log.txt"), exist_ok=True)  # Result/
    os.makedirs(CATEGORY_ROOT, exist_ok=True)   # for categorization

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

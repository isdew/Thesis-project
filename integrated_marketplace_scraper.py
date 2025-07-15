def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'ultralytics', 'selenium', 'beautifulsoup4', 'opencv-python', 
        'pyzbar', 'requests', 'torch', 'numpy', 'webdriver-manager',
        'psutil', 'pillow'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'beautifulsoup4':
                import bs4
            elif package == 'webdriver-manager':
                from webdriver_manager.firefox import GeckoDriverManager
            elif package == 'pillow':
                from PIL# Integrated Facebook Marketplace Scraper with QR and TIS Symbol Detection
# Clean version without syntax errors

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
import cv2
import numpy as np
from pathlib import Path
import torch
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from ultralytics import YOLO
import argparse
from pyzbar import pyzbar
import json
import sys
from webdriver_manager.firefox import GeckoDriverManager

# ======================== CONFIG ========================
class Config:
    # Keywords
    KEYWORDS = [
        "Power bank", "พาวเวอร์แบงค์", "PowerBank", "แบตสำรอง",
        "powerbank", "eloop", "แบตเตอรี่สำรอง", "เพาเวอร์แบงก์", "พาวเวอร์เเบง"
    ]
    
    FILTER_KEYWORDS = [
        "Power bank", "พาวเวอร์แบงค์", "PowerBank", "แบตสำรอง",
        "powerbank", "แบตเตอรี่สำรอง", "เพาเวอร์แบงก์", "พาวเวอร์เเบง", "power bank",
        "พาวเวอเเบงค์", "เพาเวอร์แบงค์"
    ]
    
    # File paths
    CSV_FILE = "integrated_results/marketplace_data.csv"
    SKIPPED_CSV = "integrated_results/skipped_posts.csv"
    IMAGE_DIR = "integrated_results/images"
    LOG_FILE = "integrated_results/scraper_log.txt"
    RESULTS_DIR = "integrated_results"
    
    # Detection model paths
    TIS_MODEL_PATH = "/Users/fadil/Downloads/TIS.pt"
    QR_YOLO_MODEL_PATH = "/Users/fadil/Downloads/capstone 2/fadil-qr-detection/yolov5/runs/train/qr_detector3/weights/best.pt"
    
    # Firefox settings - ใช้แทน Chrome
    FIREFOX_PROFILE_DIR = "/Users/fadil/Library/Application Support/Firefox/Profiles"
    
    # Scraping settings
    SCROLL_LIMIT = 15
    ZOOM_LEVEL = 0.5
    
    # Detection settings
    TIS_CONFIDENCE = 0.5
    QR_CONFIDENCE = 0.25
    
    # Feature flags
    DOWNLOAD_IMAGES = True
    ENABLE_TIS_DETECTION = True
    ENABLE_QR_DETECTION = True

# ======================== VALIDATION FUNCTIONS ========================
def validate_network_connection():
    """ตรวจสอบการเชื่อมต่อเครือข่ายกับ Facebook"""
    try:
        logging.info("🌐 Testing network connection to Facebook...")
        response = requests.get("https://www.facebook.com/favicon.ico", timeout=10)
        if response.status_code == 200:
            logging.info("✅ Network connection OK")
            return True
        else:
            logging.error(f"❌ Network test failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"❌ Network connection failed: {e}")
        return False

def check_disk_space():
    """ตรวจสอบพื้นที่ดิสก์"""
    try:
        disk_usage = psutil.disk_usage(Config.RESULTS_DIR)
        free_gb = disk_usage.free / (1024**3)
        
        if free_gb < 1.0:
            logging.error(f"❌ Low disk space: {free_gb:.2f}GB remaining")
            return False
        else:
            logging.info(f"✅ Disk space OK: {free_gb:.2f}GB available")
            return True
    except Exception as e:
        logging.error(f"❌ Could not check disk space: {e}")
        return False

def validate_runtime_config():
    """ตรวจสอบการตั้งค่าก่อนรัน"""
    errors = []
    
    if not Config.DOWNLOAD_IMAGES:
        errors.append("DOWNLOAD_IMAGES is False - no images will be saved")
    
    if not os.path.exists(Config.RESULTS_DIR):
        try:
            os.makedirs(Config.RESULTS_DIR, exist_ok=True)
        except:
            errors.append(f"Cannot create results directory: {Config.RESULTS_DIR}")
    
    if not os.access(Config.RESULTS_DIR, os.W_OK):
        errors.append(f"Cannot write to directory: {Config.RESULTS_DIR}")
    
    if errors:
        for error in errors:
            logging.error(f"❌ Config error: {error}")
        return False
    
    logging.info("✅ Runtime configuration validated")
    return True

def download_image_safely(url, temp_filename):
    """ดาวน์โหลดรูปภาพอย่างปลอดภัยพร้อม validation"""
    try:
        logging.info(f"📥 Downloading: {url}")
        
        # ใช้ requests แทน wget
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"❌ HTTP {response.status_code} for {url}")
            return False, f"HTTP {response.status_code}"
        
        # เขียนไฟล์
        with open(temp_filename, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        # ตรวจสอบไฟล์หลัง download
        if not os.path.exists(temp_filename):
            logging.error(f"❌ File not created: {temp_filename}")
            return False, "File not created"
        
        file_size = os.path.getsize(temp_filename)
        if file_size < 1000:  # น้อยกว่า 1KB
            logging.error(f"❌ File too small ({file_size} bytes): {temp_filename}")
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return False, f"File too small ({file_size} bytes)"
        
        # ตรวจสอบว่าเป็นรูปจริงหรือไม่
        try:
            with Image.open(temp_filename) as img:
                img.verify()  # ตรวจสอบ format
                logging.info(f"✅ Valid image downloaded: {file_size} bytes")
                return True, "Success"
        except Exception as e:
            logging.error(f"❌ Invalid image file: {temp_filename} - {e}")
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return False, f"Invalid image: {e}"
            
    except requests.exceptions.Timeout:
        logging.error(f"❌ Download timeout for {url}")
        return False, "Timeout"
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Download failed for {url}: {e}")
        return False, f"Request failed: {e}"
    except Exception as e:
        logging.error(f"❌ Unexpected error downloading {url}: {e}")
        return False, f"Unexpected error: {e}"

# ======================== DETECTION MODULES ========================
class TISDetector:
    def __init__(self, model_path, confidence=0.5):
        self.model = YOLO(model_path)
        self.confidence = confidence
        logging.info(f"✅ TIS Detection model loaded: {model_path}")
    
    def detect(self, image_path):
        """Detect TIS symbol in image"""
        try:
            results = self.model.predict(image_path, conf=self.confidence)
            detections = results[0].boxes.xyxy if len(results[0].boxes) > 0 else []
            
            if len(detections) > 0:
                logging.info(f"🎯 TIS symbol detected in {image_path}")
                return True, len(detections)
            else:
                logging.info(f"❌ No TIS symbol detected in {image_path}")
                return False, 0
        except Exception as e:
            logging.error(f"❌ TIS detection error for {image_path}: {e}")
            return False, 0

class QRDetector:
    def __init__(self, confidence=0.25):
        self.confidence = confidence
        logging.info("✅ QR Detection initialized")
    
    def detect_with_pyzbar(self, image_path):
        """Detect QR codes using pyzbar"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return False, 0, []
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect QR codes
            qr_codes = pyzbar.decode(gray)
            
            if qr_codes:
                qr_data = []
                for qr in qr_codes:
                    data = qr.data.decode('utf-8')
                    qr_data.append(data)
                    logging.info(f"📱 QR Code detected in {image_path}: {data}")
                
                return True, len(qr_codes), qr_data
            else:
                logging.info(f"❌ No QR code detected in {image_path}")
                return False, 0, []
                
        except Exception as e:
            logging.error(f"❌ QR detection error for {image_path}: {e}")
            return False, 0, []
    
    def detect(self, image_path):
        """Main QR detection method"""
        return self.detect_with_pyzbar(image_path)

# ======================== INTEGRATED DETECTOR ========================
class IntegratedDetector:
    def __init__(self):
        self.tis_detector = None
        self.qr_detector = None
        
        # Initialize detectors based on config
        if Config.ENABLE_TIS_DETECTION:
            try:
                self.tis_detector = TISDetector(Config.TIS_MODEL_PATH, Config.TIS_CONFIDENCE)
            except Exception as e:
                logging.error(f"❌ Failed to load TIS detector: {e}")
        
        if Config.ENABLE_QR_DETECTION:
            try:
                self.qr_detector = QRDetector(Config.QR_CONFIDENCE)
            except Exception as e:
                logging.error(f"❌ Failed to load QR detector: {e}")
    
    def analyze_image(self, image_path):
        """Analyze image for both TIS and QR detection"""
        results = {
            'tis_detected': False,
            'tis_count': 0,
            'qr_detected': False,
            'qr_count': 0,
            'qr_data': []
        }
        
        # TIS Detection
        if self.tis_detector and Config.ENABLE_TIS_DETECTION:
            tis_found, tis_count = self.tis_detector.detect(image_path)
            results['tis_detected'] = tis_found
            results['tis_count'] = tis_count
        
        # QR Detection
        if self.qr_detector and Config.ENABLE_QR_DETECTION:
            qr_found, qr_count, qr_data = self.qr_detector.detect(image_path)
            results['qr_detected'] = qr_found
            results['qr_count'] = qr_count
            results['qr_data'] = qr_data
        
        return results

# ======================== ENHANCED SCRAPER ========================
class EnhancedMarketplaceScraper:
    def __init__(self):
        self.detector = IntegratedDetector()
        self.setup_directories()
        self.setup_logging()
    
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(Config.RESULTS_DIR, exist_ok=True)
        os.makedirs(Config.IMAGE_DIR, exist_ok=True)
        os.makedirs(f"{Config.IMAGE_DIR}/with_tis", exist_ok=True)
        os.makedirs(f"{Config.IMAGE_DIR}/with_qr", exist_ok=True)
        os.makedirs(f"{Config.IMAGE_DIR}/with_both", exist_ok=True)
        os.makedirs(f"{Config.IMAGE_DIR}/no_detection", exist_ok=True)
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(Config.LOG_FILE, mode='w', encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
    
    def setup_firefox(self):
        """Setup Firefox driver with profile that has Facebook login"""
        logging.info("🦊 Preparing Firefox setup...")
        
        # Kill Firefox processes
        os.system("pkill -f Firefox")
        time.sleep(3)
        
        # Find Firefox profiles
        try:
            profiles = [d for d in os.listdir(Config.FIREFOX_PROFILE_DIR) 
                       if os.path.isdir(os.path.join(Config.FIREFOX_PROFILE_DIR, d))]
            
            if not profiles:
                logging.error("❌ No Firefox profiles found!")
                raise Exception("No Firefox profiles found")
            
            logging.info("📋 Available Firefox profiles:")
            for profile in profiles:
                logging.info(f"   - {profile}")
            
            # ใช้ profile แรกที่เจอ (หรือสามารถปรับให้เลือกได้)
            selected_profile = profiles[0]
            profile_path = os.path.join(Config.FIREFOX_PROFILE_DIR, selected_profile)
            
            logging.info(f"✅ Using profile: {selected_profile}")
            logging.info(f"📁 Profile path: {profile_path}")
            
        except Exception as e:
            logging.error(f"❌ Error finding Firefox profiles: {e}")
            raise
        
        # Firefox options
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.add_argument("--width=1920")
        firefox_options.add_argument("--height=1080")
        
        # ใช้ profile ที่มี Facebook login
        firefox_options.add_argument("-profile")
        firefox_options.add_argument(profile_path)

        try:
            # Use webdriver-manager for GeckoDriver
            logging.info("📦 Using webdriver-manager for GeckoDriver...")
            service = Service(GeckoDriverManager().install())
            
            driver = webdriver.Firefox(service=service, options=firefox_options)
            logging.info("✅ Firefox driver initialized")
            
            # Wait for Firefox to be ready
            time.sleep(3)
            driver.maximize_window()
            
            # Try to navigate to Facebook
            success = self.navigate_to_facebook(driver)
            
            if success:
                logging.info("✅ Facebook navigation successful")
            else:
                logging.warning("⚠️  Facebook navigation failed, but Firefox is available")
            
            return driver
            
        except Exception as e:
            logging.error(f"❌ Failed to setup Firefox: {e}")
            raise
    
    def navigate_to_facebook(self, driver):
        """Try multiple methods to navigate to Facebook with detailed debugging"""
        facebook_urls = [
            "https://www.facebook.com",
            "https://facebook.com", 
            "https://m.facebook.com"
        ]
        
        # Debug info
        logging.info(f"🔍 DEBUG: Current URL before navigation: {driver.current_url}")
        logging.info(f"🔍 DEBUG: Window handles: {len(driver.window_handles)}")
        
        for i, url in enumerate(facebook_urls, 1):
            try:
                logging.info(f"🌐 Method {i}: Trying {url}...")
                
                if i > 1:  # For methods 2 and 3, open new tab
                    logging.info(f"🔍 DEBUG: Opening new tab (method {i})")
                    driver.execute_script("window.open('about:blank', '_blank');")
                    time.sleep(2)
                    
                    logging.info(f"🔍 DEBUG: Available windows: {len(driver.window_handles)}")
                    driver.switch_to.window(driver.window_handles[-1])
                    logging.info(f"🔍 DEBUG: Switched to window, current URL: {driver.current_url}")
                
                # Navigate
                logging.info(f"🔍 DEBUG: Starting navigation to {url}")
                driver.get(url)
                
                # Wait and check multiple times
                for wait_time in [3, 5, 8, 10]:
                    time.sleep(wait_time - (3 if wait_time == 3 else wait_time - 5 if wait_time == 5 else wait_time - 8))
                    current_url = driver.current_url
                    page_title = driver.title
                    
                    logging.info(f"🔍 DEBUG: After {wait_time}s - URL: {current_url}")
                    logging.info(f"🔍 DEBUG: After {wait_time}s - Title: {page_title}")
                    
                    if "facebook.com" in current_url:
                        logging.info(f"✅ Success at {wait_time}s! Current URL: {current_url}")
                        
                        # Additional debug - check page content
                        page_source_length = len(driver.page_source)
                        logging.info(f"🔍 DEBUG: Page source length: {page_source_length}")
                        
                        # Check for specific elements
                        try:
                            # Check for various Facebook elements
                            marketplace_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/marketplace')]")
                            login_forms = driver.find_elements(By.XPATH, "//input[@type='email']")
                            facebook_logo = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Facebook')]")
                            navigation_bar = driver.find_elements(By.XPATH, "//div[@role='banner']")
                            
                            logging.info(f"🔍 DEBUG: Found {len(marketplace_links)} marketplace links")
                            logging.info(f"🔍 DEBUG: Found {len(login_forms)} login forms")
                            logging.info(f"🔍 DEBUG: Found {len(facebook_logo)} Facebook logos")
                            logging.info(f"🔍 DEBUG: Found {len(navigation_bar)} navigation bars")
                            
                            if marketplace_links:
                                logging.info("✅ User appears to be logged in (found marketplace)")
                                return True
                            elif login_forms:
                                logging.warning("⚠️  User needs to login (found login form)")
                                logging.info("💡 Please login to Facebook manually in this browser window")
                                
                                # Wait for user to login
                                input("Press Enter after you have logged in to Facebook...")
                                
                                # Check again after login
                                marketplace_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/marketplace')]")
                                if marketplace_links:
                                    logging.info("✅ Login successful!")
                                    return True
                                else:
                                    logging.warning("⚠️  Still no marketplace found after login")
                                    return True  # Continue anyway
                            else:
                                logging.info("📄 Facebook page loaded, but status unclear")
                                
                                # Show some page content for debugging
                                try:
                                    body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
                                    logging.info(f"🔍 DEBUG: Page content preview: {body_text}")
                                except:
                                    pass
                                
                                return True  # Consider it successful if we reached Facebook
                            
                        except Exception as e:
                            logging.warning(f"⚠️  Could not check page elements: {e}")
                            return True  # Still consider it successful
                        
                        return True
                    else:
                        logging.info(f"❌ Still not at Facebook after {wait_time}s. Current: {current_url}")
                        
                        # Check if we got redirected somewhere
                        if current_url and current_url != "data:," and current_url != "about:blank":
                            logging.info(f"🔍 DEBUG: Got redirected to: {current_url}")
                            
                            # Check if it's a Facebook-related redirect
                            if any(domain in current_url for domain in ['facebook', 'meta', 'fb']):
                                logging.info("🔍 DEBUG: Looks like a Facebook-related page")
                                return True
                        
                # Final check after all waits
                final_url = driver.current_url
                if "facebook.com" not in final_url:
                    logging.error(f"❌ Method {i} failed. Final URL: {final_url}")
                    
                    # Take screenshot for debugging
                    try:
                        screenshot_path = f"debug_screenshot_method_{i}.png"
                        driver.save_screenshot(screenshot_path)
                        logging.info(f"📸 Screenshot saved: {screenshot_path}")
                    except:
                        pass
                        
            except Exception as e:
                logging.warning(f"❌ Method {i} failed with exception: {e}")
                continue
        
        logging.error("❌ All Facebook navigation methods failed")
        
        # Final debug info
        try:
            final_url = driver.current_url
            final_title = driver.title
            logging.info(f"🔍 DEBUG: Final URL: {final_url}")
            logging.info(f"🔍 DEBUG: Final Title: {final_title}")
            
            # Save final screenshot
            driver.save_screenshot("debug_final_screenshot.png")
            logging.info("📸 Final screenshot saved: debug_final_screenshot.png")
            
        except Exception as e:
            logging.error(f"❌ Could not get final debug info: {e}")
        
        return False
    
    def save_csv_row(self, filename, row, header=None):
        """Save row to CSV file"""
        file_exists = os.path.exists(filename)
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists and header:
                writer.writerow(header)
            writer.writerow(row)
    
    def normalize_text(self, text):
        """Normalize text for comparison"""
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[\u200b\u200c\u200d\uFEFF\uFFFC\uFFFD]", '', text)
        text = re.sub(r"\s+", ' ', text)
        return text.lower().strip()
    
    def sanitize_filename(self, title):
        """Sanitize filename for saving"""
        return re.sub(r'[<>:"/\\|?*]', '_', title)[:100]
    
    def organize_image_by_detection(self, image_path, detection_results):
        """Organize images into folders based on detection results"""
        filename = os.path.basename(image_path)
        
        if detection_results['tis_detected'] and detection_results['qr_detected']:
            target_dir = f"{Config.IMAGE_DIR}/with_both"
        elif detection_results['tis_detected']:
            target_dir = f"{Config.IMAGE_DIR}/with_tis"
        elif detection_results['qr_detected']:
            target_dir = f"{Config.IMAGE_DIR}/with_qr"
        else:
            target_dir = f"{Config.IMAGE_DIR}/no_detection"
        
        target_path = os.path.join(target_dir, filename)
        
        if Config.DOWNLOAD_IMAGES:
            shutil.copy2(image_path, target_path)
            logging.info(f"📁 Organized image to: {target_dir}")
    
    def search_facebook(self, driver, query):
        """Search Facebook marketplace using direct URL"""
        try:
            # ใช้ URL โดยตรงแทนการพิมพ์ใน search box
            search_url = f"https://www.facebook.com/marketplace/search/?query={query.replace(' ', '%20')}"
            
            logging.info(f"🔍 Searching for keyword: {query}")
            logging.info(f"🌐 Using direct URL: {search_url}")
            
            # Navigate ไปที่ search URL โดยตรง
            driver.get(search_url)
            time.sleep(10)  # รอให้หน้าโหลดเสร็จ
            
            current_url = driver.current_url
            logging.info(f"📍 Current URL after search: {current_url}")
            
            # ตรวจสอบว่าเข้าหน้า search ได้หรือไม่
            if "marketplace" in current_url and ("search" in current_url or "query" in current_url):
                logging.info("✅ Successfully loaded search results page")
            else:
                logging.warning("⚠️  Search page may not have loaded properly")
                
                # ลองวิธีอื่น - ไปหน้า marketplace ก่อนแล้วค่อย search
                logging.info("🔄 Trying alternative method...")
                driver.get("https://www.facebook.com/marketplace")
                time.sleep(5)
                
                # ลองใช้ search URL อีกครั้ง
                driver.get(search_url)
                time.sleep(10)
                
            # รอให้ search results โหลดเสร็จ
            logging.info("⏳ Waiting for search results to load...")
            time.sleep(8)

            # Scroll and collect links
            links = set()
            skipped = set()

            for scroll in range(Config.SCROLL_LIMIT):
                logging.info(f"🔄 Scroll {scroll + 1}/{Config.SCROLL_LIMIT} for keyword: {query}")
                time.sleep(8)
                
                try:
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.find_all("a", href=True)
                    
                    new_links_found = 0
                    
                    for item in items:
                        href = item["href"]
                        if "/marketplace/item/" not in href:
                            continue

                        link = f"https://www.facebook.com{href.split('?')[0]}"
                        
                        # หาชื่อสินค้า (ลองหลาย selector)
                        title_elem = (
                            item.find("span", class_="x1lliihq x6ikm8r x10wlt62 x1n2onr6") or
                            item.find("span", class_="x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x x14z4hjw x3x7a5m xngnso2 x1qb5hxa x1xlr1w8 xzsf02u") or
                            item.find_next("span")
                        )
                        title = title_elem.text.strip().lower() if title_elem else ""

                        if title and not any(k.lower() in title for k in Config.FILTER_KEYWORDS):
                            skipped.add((title, link))
                            continue
                            
                        if link not in links:
                            links.add(link)
                            new_links_found += 1

                    logging.info(f"   📊 Found {new_links_found} new links this scroll")
                    
                    # หากไม่เจอ links ใหม่ใน 3 scroll ติดต่อกัน
                    if new_links_found == 0:
                        logging.info(f"   ⏭️  No new links found in this scroll")
                    
                except Exception as e:
                    logging.error(f"❌ Error during scroll {scroll + 1}: {e}")

                # Scroll down
                try:
                    driver.execute_script("window.scrollBy(0, 1500);")
                    time.sleep(3)
                except:
                    pass

            # Save skipped posts
            for skip in skipped:
                self.save_csv_row(Config.SKIPPED_CSV, list(skip))

            logging.info(f"📊 Keyword '{query}' - Found: {len(links)} links, Skipped: {len(skipped)}")
            return links, skipped
            
        except Exception as e:
            logging.error(f"❌ Error in search_facebook for keyword '{query}': {e}")
            return set(), set()
    
    def scrape_post_with_detection(self, driver, post_url):
        """Enhanced post scraping with integrated detection and early stop"""
        logging.info(f"🔍 Processing post: {post_url}")
        
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
            logging.warning("⚠ Title not found, skipping post")
            return

        safe_title = self.sanitize_filename(title)
        
        # Find images
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

        total_images = len(img_elements)
        if total_images == 0:
            logging.warning("⚠ No images found in post")
            return

        logging.info(f"📸 Found {total_images} images in post")
        
        matched_urls = []
        all_detection_results = []
        post_detection_summary = {
            'tis_detected': False,
            'qr_detected': False,
            'tis_count': 0,
            'qr_count': 0,
            'total_qr_data': []
        }
        
        # Early stop tracking
        failed_downloads = 0
        successful_downloads = 0
        max_failures = min(3, max(1, total_images // 2))  # หยุดถ้า fail > 50% หรือ 3 รูป

        for idx, img in enumerate(img_elements):
            url = img.get_attribute("src")
            if not url:
                logging.warning(f"⚠ Image {idx+1}: No src attribute")
                failed_downloads += 1
                continue
                
            matched_urls.append(url)
            logging.info(f"🔄 Processing Image {idx+1}/{total_images}")
            
            # Generate temp filename
            temp_filename = os.path.join(Config.IMAGE_DIR, f"temp_{safe_title}_{idx}_{int(time.time())}.jpg")
            
            # Download with enhanced error handling
            download_success, error_msg = download_image_safely(url, temp_filename)
            
            if not download_success:
                logging.error(f"❌ Image {idx+1} download failed: {error_msg}")
                failed_downloads += 1
                
                # Early stop check
                if failed_downloads >= max_failures:
                    logging.error(f"⏹️  TOO MANY DOWNLOAD FAILURES ({failed_downloads}/{idx+1})")
                    logging.error(f"⏹️  STOPPING POST PROCESSING TO SAVE TIME")
                    logging.error(f"⏹️  Post: {post_url}")
                    
                    # Clean up any temp files
                    for temp_file in os.listdir(Config.IMAGE_DIR):
                        if temp_file.startswith(f"temp_{safe_title}"):
                            try:
                                os.remove(os.path.join(Config.IMAGE_DIR, temp_file))
                            except:
                                pass
                    return
                
                continue
            
            successful_downloads += 1
            logging.info(f"✅ Image {idx+1} downloaded successfully")
            
            # Perform integrated detection
            try:
                detection_results = self.detector.analyze_image(temp_filename)
                all_detection_results.append(detection_results)
                
                # Update post summary
                if detection_results['tis_detected']:
                    post_detection_summary['tis_detected'] = True
                    post_detection_summary['tis_count'] += detection_results['tis_count']
                
                if detection_results['qr_detected']:
                    post_detection_summary['qr_detected'] = True
                    post_detection_summary['qr_count'] += detection_results['qr_count']
                    post_detection_summary['total_qr_data'].extend(detection_results['qr_data'])
                
                logging.info(f"🔍 Image {idx+1} Analysis - TIS: {'✅' if detection_results['tis_detected'] else '❌'}, "
                           f"QR: {'✅' if detection_results['qr_detected'] else '❌'}")
                
            except Exception as e:
                logging.error(f"❌ Detection failed for image {idx+1}: {e}")
                detection_results = {
                    'tis_detected': False, 'tis_count': 0,
                    'qr_detected': False, 'qr_count': 0, 'qr_data': []
                }
            
            # Organize and save image if needed
            if Config.DOWNLOAD_IMAGES:
                try:
                    permanent_filename = os.path.join(Config.IMAGE_DIR, f"{safe_title}_{idx}_{int(time.time())}.jpg")
                    shutil.move(temp_filename, permanent_filename)
                    self.organize_image_by_detection(permanent_filename, detection_results)
                    logging.info(f"📁 Image {idx+1} organized successfully")
                except Exception as e:
                    logging.error(f"❌ Failed to organize image {idx+1}: {e}")
            else:
                # ลบไฟล์ temp หากไม่ต้องการเก็บ
                try:
                    os.remove(temp_filename)
                except:
                    pass
            
            time.sleep(random.uniform(1, 2))

        # Final validation
        if successful_downloads == 0:
            logging.error(f"❌ NO IMAGES DOWNLOADED from post: {post_url}")
            return
            
        logging.info(f"📊 Post Summary - Downloads: {successful_downloads}/{total_images}, "
                    f"Failures: {failed_downloads}")

        # Save comprehensive results
        if matched_urls:
            qr_data_str = " | ".join(post_detection_summary['total_qr_data']) if post_detection_summary['total_qr_data'] else "None"
            
            row = [
                title,
                post_url,
                " | ".join(matched_urls),
                "Yes" if post_detection_summary['tis_detected'] else "No",
                post_detection_summary['tis_count'],
                "Yes" if post_detection_summary['qr_detected'] else "No",
                post_detection_summary['qr_count'],
                qr_data_str,
                successful_downloads,
                failed_downloads
            ]
            
            header = [
                "Title", "Post Link", "Photo Links", "TIS Detected", "TIS Count",
                "QR Detected", "QR Count", "QR Data", "Successful Downloads", "Failed Downloads"
            ]
            
            self.save_csv_row(Config.CSV_FILE, row, header=header)
            
            logging.info(f"✅ Saved results for: {title}")
            logging.info(f"   📊 TIS: {'Yes' if post_detection_summary['tis_detected'] else 'No'} "
                        f"(Count: {post_detection_summary['tis_count']})")
            logging.info(f"   📱 QR: {'Yes' if post_detection_summary['qr_detected'] else 'No'} "
                        f"(Count: {post_detection_summary['qr_count']})")
        else:
            logging.warning("⚠ No images processed for analysis.")
    
    def run_integrated_scraping(self):
        """Main method to run integrated scraping with detection"""
        logging.info("🚀 Starting Integrated Facebook Marketplace Scraper with Detection (Firefox)")
        
        driver = self.setup_firefox()  # เปลี่ยนจาก setup_chrome เป็น setup_firefox
        
        all_links = set()
        all_skipped = set()
        keyword_summary = defaultdict(lambda: {'found': 0, 'skipped': 0})

        # Search for all keywords
        for keyword in Config.KEYWORDS:
            logging.info(f"🔍 Searching for keyword: {keyword}")
            found, skipped = self.search_facebook(driver, keyword)
            all_links.update(found)
            all_skipped.update(skipped)
            keyword_summary[keyword]['found'] = len(found)
            keyword_summary[keyword]['skipped'] = len(skipped)

        # Print search summary
        self.print_search_summary(keyword_summary, len(all_links), len(all_skipped))

        # Scrape all found posts with integrated detection
        logging.info(f"🎯 Starting detailed scraping and detection for {len(all_links)} posts")
        
        for idx, link in enumerate(all_links):
            logging.info(f"📍 Processing {idx+1}/{len(all_links)}: {link}")
            try:
                self.scrape_post_with_detection(driver, link)
            except Exception as e:
                logging.error(f"❌ Failed to process {link}: {e}")
            time.sleep(random.uniform(2, 4))
        
        driver.quit()
        
        # Generate final report
        self.generate_final_report()
        logging.info("🎉 Integrated scraping and detection completed!")
    
    def print_search_summary(self, keyword_summary, total_links, total_skipped):
        """Print search summary"""
        logging.info("📊 SEARCH SUMMARY")
        logging.info("="*60)
        
        for keyword, counts in keyword_summary.items():
            logging.info(f"🔍 {keyword}:")
            logging.info(f"   ✅ Found: {counts['found']}")
            logging.info(f"   ❌ Skipped: {counts['skipped']}")
        
        logging.info(f"\n📈 OVERALL TOTALS:")
        logging.info(f"   📌 Unique links to process: {total_links}")
        logging.info(f"   ⏭️ Total skipped: {total_skipped}")
        logging.info("="*60 + "\n")
    
    def generate_final_report(self):
        """Generate final detection report"""
        if not os.path.exists(Config.CSV_FILE):
            return
        
        report_file = os.path.join(Config.RESULTS_DIR, "detection_report.json")
        
        stats = {
            'total_posts': 0,
            'posts_with_tis': 0,
            'posts_with_qr': 0,
            'posts_with_both': 0,
            'total_images': 0,
            'total_tis_detections': 0,
            'total_qr_detections': 0
        }
        
        try:
            with open(Config.CSV_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats['total_posts'] += 1
                    
                    if row.get('TIS Detected') == 'Yes':
                        stats['posts_with_tis'] += 1
                        stats['total_tis_detections'] += int(row.get('TIS Count', 0))
                    
                    if row.get('QR Detected') == 'Yes':
                        stats['posts_with_qr'] += 1
                        stats['total_qr_detections'] += int(row.get('QR Count', 0))
                    
                    if row.get('TIS Detected') == 'Yes' and row.get('QR Detected') == 'Yes':
                        stats['posts_with_both'] += 1
                    
                    stats['total_images'] += int(row.get('Total Images', 0))
        
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            logging.info("📋 FINAL DETECTION REPORT:")
            logging.info(f"   📝 Total posts processed: {stats['total_posts']}")
            logging.info(f"   🎯 Posts with TIS symbol: {stats['posts_with_tis']}")
            logging.info(f"   📱 Posts with QR code: {stats['posts_with_qr']}")
            logging.info(f"   🎯📱 Posts with both: {stats['posts_with_both']}")
            logging.info(f"   📸 Total images analyzed: {stats['total_images']}")
            logging.info(f"   🎯 Total TIS detections: {stats['total_tis_detections']}")
            logging.info(f"   📱 Total QR detections: {stats['total_qr_detections']}")
            
        except Exception as e:
            logging.error(f"❌ Failed to generate report: {e}")

# ======================== REQUIREMENTS CHECK ========================
def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'ultralytics', 'selenium', 'beautifulsoup4', 'opencv-python', 
        'pyzbar', 'requests', 'torch', 'numpy', 'webdriver-manager',
        'psutil', 'pillow'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'beautifulsoup4':
                import bs4
            elif package == 'webdriver-manager':
                from webdriver_manager.firefox import GeckoDriverManager
            elif package == 'pillow':
                from PIL import Image
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n📦 Install them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def validate_config():
    """Validate configuration settings"""
    errors = []
    warnings = []
    
    # Check model paths
    if Config.ENABLE_TIS_DETECTION and not os.path.exists(Config.TIS_MODEL_PATH):
        errors.append(f"TIS model not found: {Config.TIS_MODEL_PATH}")
    
    if Config.ENABLE_QR_DETECTION and not os.path.exists(Config.QR_YOLO_MODEL_PATH):
        errors.append(f"QR YOLO model not found: {Config.QR_YOLO_MODEL_PATH}")
    
    # Check Firefox profile directory
    if not os.path.exists(Config.FIREFOX_PROFILE_DIR):
        errors.append(f"Firefox profile directory not found: {Config.FIREFOX_PROFILE_DIR}")
    else:
        try:
            profiles = [d for d in os.listdir(Config.FIREFOX_PROFILE_DIR) 
                       if os.path.isdir(os.path.join(Config.FIREFOX_PROFILE_DIR, d))]
            if profiles:
                warnings.append(f"Found {len(profiles)} Firefox profiles:")
                for profile in profiles:
                    warnings.append(f"  - {profile}")
            else:
                errors.append("No Firefox profiles found")
        except:
            errors.append("Could not list Firefox profiles")
    
    # Check Firefox installation
    try:
        firefox_check = os.system("which firefox > /dev/null 2>&1")
        if firefox_check == 0:
            warnings.append("✅ Firefox is installed")
        else:
            warnings.append("⚠️  Firefox may not be installed or not in PATH")
    except:
        warnings.append("Could not check Firefox installation")
    
    warnings.append("✅ Using webdriver-manager - GeckoDriver will be managed automatically")
    
    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        print("\n💡 Tips:")
        print("   - Install Firefox: brew install firefox")
        print("   - Create Firefox profile with Facebook login")
        print("   - Make sure model files are downloaded")
        return False
    
    if warnings:
        print("⚠️  Configuration info:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    return True

# ======================== MAIN EXECUTION ========================
def main():
    """Main execution function"""
    print("🦊 Integrated Facebook Marketplace Scraper with Detection (Firefox)")
    print("=" * 70)
    
    # Check requirements
    print("🔍 Checking requirements...")
    if not check_requirements():
        print("❌ Please install missing packages first!")
        return
    
    print("✅ All packages installed")
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Integrated Facebook Marketplace Scraper with Detection")
    parser.add_argument("--no-tis", action="store_true", help="Disable TIS symbol detection")
    parser.add_argument("--no-qr", action="store_true", help="Disable QR code detection")
    parser.add_argument("--no-download", action="store_true", help="Don't save images permanently")
    parser.add_argument("--scroll-limit", type=int, default=15, help="Number of scrolls per keyword")
    
    args = parser.parse_args()
    
    # Update config based on arguments
    if args.no_tis:
        Config.ENABLE_TIS_DETECTION = False
        print("⚠️  TIS detection disabled")
    if args.no_qr:
        Config.ENABLE_QR_DETECTION = False
        print("⚠️  QR detection disabled")
    if args.no_download:
        Config.DOWNLOAD_IMAGES = False
        print("⚠️  Image saving disabled")
    if args.scroll_limit:
        Config.SCROLL_LIMIT = args.scroll_limit
        print(f"🔄 Scroll limit set to: {args.scroll_limit}")
    
    # Validate configuration
    print("🔍 Validating configuration...")
    if not validate_config():
        print("❌ Please fix configuration errors first!")
        return
    
    print("✅ Configuration valid")
    print(f"🦊 Using Firefox with profile detection")
    
    # Show what will be detected
    detection_modes = []
    if Config.ENABLE_TIS_DETECTION:
        detection_modes.append("TIS Symbol")
    if Config.ENABLE_QR_DETECTION:
        detection_modes.append("QR Code")
    
    if detection_modes:
        print(f"🎯 Detection modes: {', '.join(detection_modes)}")
    else:
        print("⚠️  No detection enabled - will only scrape images")
    
    print(f"📁 Results will be saved to: {Config.RESULTS_DIR}")
    print("=" * 70)
    
    # Ask for confirmation
    response = input("\n▶️  Ready to start scraping? (y/N): ").strip().lower()
    if response != 'y' and response != 'yes':
        print("❌ Cancelled by user")
        return
    
    # Create and run scraper
    try:
        scraper = EnhancedMarketplaceScraper()
        scraper.run_integrated_scraping()
        
        print("\n🎉 Scraping completed successfully!")
        print(f"📊 Check results in: {Config.RESULTS_DIR}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    # Set up error handling for imports
    try:
        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all required packages are installed:")
        print("pip install ultralytics selenium beautifulsoup4 opencv-python pyzbar requests torch numpy webdriver-manager psutil pillow")
        print("💡 And make sure Firefox is installed: brew install firefox")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Check the error log for more details")
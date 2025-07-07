from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import random
import pandas as pd
import os
import sys
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime

# Setup Chrome WebDriver with profile
CHROME_DRIVER_PATH = "/Users/fadil/Downloads/chromedriver-mac-arm642/chromedriver"
PROGRESS_FILE = "fb_crawler_progress.json"
OUTPUT_FILE = "facebook_powerbank_all_data.csv"

# Keywords for search
SEARCH_KEYWORDS = [
    "Power Bank",
    "พาวเวอร์แบงค์",
    "พาวเวอร์แบงก์",
    "เพาเวอร์แบงค์",
    "เพาเวอร์แบงก์",
    "แบตเตอรี่สำรอง",
    "Powerbank",
    "แบตสำรอง",
    "Eloop"
]

# Keywords for filtering posts
FILTER_KEYWORDS = ["Power Bank","พาวเวอร์แบงค์","พาวเวอร์แบงก์","เพาเวอร์แบงค์","เพาเวอร์แบงก์","แบตเตอรี่สำรอง","Powerbank","แบตสำรอง","Eloop", "แบตฯ",  "พาวเวอร์", "พาวเวอร์แบ็งค์", "พาเวอร์แบงค์"]

# Setup Chrome WebDriver with profile
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--user-data-dir=/Users/fadil/Library/Application Support/Google/Chrome")
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-notifications")  # Disable Facebook notifications

# Function to load progress if exists
def load_progress():
    default_progress = {"last_keyword_index": 0, "processed_urls": []}
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as file:
                progress = json.load(file)
                # Make sure the progress file has the expected structure
                if "last_keyword_index" not in progress:
                    progress["last_keyword_index"] = 0
                if "processed_urls" not in progress:
                    progress["processed_urls"] = []
                return progress
        except Exception as e:
            print(f"Error loading progress file: {str(e)}. Using default progress.")
            return default_progress
    return default_progress

# Function to save progress
def save_progress(keyword_index, processed_urls):
    with open(PROGRESS_FILE, 'w') as file:
        json.dump({"last_keyword_index": keyword_index, "processed_urls": processed_urls}, file)

# Function to check if a post contains any of the filter keywords
def contains_filter_keyword(text):
    if not text:
        return False
    
    text_lower = text.lower()
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    # More lenient matching - if we're not finding posts, assume most are relevant
    print(f"Post text (first 100 chars): {text[:100] if text else 'Empty'}...")
    return True  # Make all posts relevant for now to catch more data

# Function to extract post permalink URL
def extract_post_url(post_element):
    try:
        # List of patterns that might indicate a post URL
        post_url_patterns = [
            "/posts/",
            "/permalink/",
            "/photo.php",
            "/video.php",
            "/share/p/",
            "/share/v/",
            "/reel/"
        ]
        
        # Try to find direct post links - approach 1: look for specific attributes
        try:
            links = post_element.find_elements(By.CSS_SELECTOR, "a[href*='/posts/'], a[href*='/permalink/'], a[href*='/photo.php'], a[href*='/video.php'], a[href*='/share/p/'], a[href*='/share/v/'], a[href*='/reel/']")
            for link in links:
                href = link.get_attribute("href")
                if href and any(pattern in href for pattern in post_url_patterns):
                    # Clean the URL by removing tracking parameters
                    clean_url = href.split('?')[0]
                    print(f"Found direct post URL: {clean_url}")
                    return clean_url
        except:
            pass
            
        # Approach 2: look for timestamp links or 'aria-label' containing time references
        try:
            time_links = post_element.find_elements(By.CSS_SELECTOR, "a[role='link'][aria-label*='at'], a[role='link'][aria-label*='เมื่อ'], a[aria-label*='hour'], a[aria-label*='minute'], a[aria-label*='วัน'], a[aria-label*='ชั่วโมง'], a[aria-label*='นาที']")
            for link in time_links:
                href = link.get_attribute("href")
                if href and any(pattern in href for pattern in post_url_patterns):
                    clean_url = href.split('?')[0]
                    print(f"Found timestamp URL: {clean_url}")
                    return clean_url
        except:
            pass
            
        # Approach 3: Get any link that might be a post
        all_links = post_element.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            href = link.get_attribute("href")
            if href and any(pattern in href for pattern in post_url_patterns):
                clean_url = href.split('?')[0]
                print(f"Found potential post URL: {clean_url}")
                return clean_url
                
        # Approach 4: Special case for story URLs - convert if possible
        all_links = post_element.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            href = link.get_attribute("href")
            if href and "/stories/" in href:
                print(f"Found story URL, cannot convert to post URL: {href}")
                # Don't return story URLs as they're not what the user wants
                return None
                
        return None
    except Exception as e:
        print(f"Error extracting post URL: {str(e)}")
        return None

# Function to extract post data
def extract_post_data(post_element):
    try:
        # Extract post URL only
        post_url = extract_post_url(post_element)
        
        if not post_url:
            return None
            
        # We only care about the URL, as requested by the user
        return {
            "post_url": post_url,
            "search_keyword": current_keyword,
            "crawl_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Error extracting post data: {str(e)}")
        return None

# Initialize WebDriver
service = Service(CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Force reset progress file
import os
if os.path.exists(PROGRESS_FILE):
    print(f"Deleting existing progress file: {PROGRESS_FILE}")
    os.remove(PROGRESS_FILE)
    print("Progress file deleted")

# Reset progress completely
last_keyword_index = 0
processed_urls = set()
print("Progress reset to start from beginning")

# Save empty progress to ensure it's properly initialized
save_progress(0, [])

# Prepare DataFrame to store results - simplified structure
if os.path.exists(OUTPUT_FILE):
    all_posts_df = pd.read_csv(OUTPUT_FILE)
else:
    all_posts_df = pd.DataFrame(columns=["post_url", "search_keyword", "crawl_date"])
    
# Set to track unique URLs already processed
if "post_url" in all_posts_df.columns:
    processed_urls.update(all_posts_df["post_url"].dropna().tolist())

try:
    # Login to Facebook if necessary (assuming already logged in via profile)
    driver.get("https://www.facebook.com")
    time.sleep(5)  # Wait for page to load
    
    # Process each search keyword
    for keyword_index, current_keyword in enumerate(SEARCH_KEYWORDS[last_keyword_index:], start=last_keyword_index):
        print(f"Processing keyword {keyword_index+1}/{len(SEARCH_KEYWORDS)}: {current_keyword}")
        
        # Navigate to Facebook search posts
        search_url = f"https://www.facebook.com/search/posts/?q={current_keyword.replace(' ', '%20')}"
        print(f"Navigating to search URL: {search_url}")
        driver.get(search_url)
        print("Page loaded, waiting for content...")
        time.sleep(random.uniform(5, 8))  # Increased wait time for search results to load
        
        # Try to inject a scroll event to trigger post loading - Facebook sometimes requires user interaction
        print("Injecting initial scroll events to trigger content loading...")
        try:
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(2)
            driver.execute_script("window.scrollBy(0, 300);") 
            time.sleep(2)
            driver.execute_script("window.scrollBy(0, -100);") 
            time.sleep(2)
            print("Initial scroll events completed")
        except Exception as e:
            print(f"Error during initial scroll: {str(e)}")
        
        # Scroll to load more posts (adjust number of scrolls as needed)
        print("Starting main scrolling loop...")
        scroll_count = 0
        max_scrolls = 50  # Limit to prevent infinite scrolling
        post_count = 0
        new_posts_count = 0
        
        while scroll_count < max_scrolls:
            print(f"\nScroll #{scroll_count+1}: Searching for posts...")
            
            # Find all post elements - try multiple selectors to catch all possible posts
            posts_main = driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
            print(f"Found {len(posts_main)} posts with main selector")
            
            # Try alternative selectors if nothing found with main selector
            posts_alt = []
            if len(posts_main) == 0:
                print("Trying alternative selectors...")
                alt_selectors = [
                    "div[data-pagelet*='FeedUnit']",
                    "div.x1lliihq",  # Facebook feed posts often have this class
                    "div.x1yztbdb",  # Another common Facebook post class
                    "div.x78zum5",   # Common feed item class
                    "div[data-testid='post_container']",
                    "div.feed_story" # Legacy selector
                ]
                
                for selector in alt_selectors:
                    try:
                        found_posts = driver.find_elements(By.CSS_SELECTOR, selector)
                        if found_posts:
                            print(f"Found {len(found_posts)} posts with selector: {selector}")
                            posts_alt.extend(found_posts)
                    except Exception as e:
                        print(f"Error with selector {selector}: {str(e)}")
            
            # Combine and deduplicate posts
            all_posts = list(posts_main)
            for post in posts_alt:
                if post not in all_posts:
                    all_posts.append(post)
            
            posts = all_posts
            
            current_post_count = len(posts)
            
            print(f"Found {current_post_count} posts, processed {post_count} posts")
            
            # Check if we found more posts
            if current_post_count > post_count:
                # Process new posts
                for post in posts[post_count:current_post_count]:
                    try:
                        post_data = extract_post_data(post)
                        
                        if post_data and post_data["post_url"] and post_data["post_url"] not in processed_urls:
                            all_posts_df = pd.concat([all_posts_df, pd.DataFrame([post_data])], ignore_index=True)
                            processed_urls.add(post_data["post_url"])
                            new_posts_count += 1
                            
                            # Save periodically
                            if new_posts_count % 5 == 0:
                                all_posts_df.to_csv(OUTPUT_FILE, index=False)
                                save_progress(keyword_index, list(processed_urls))
                                print(f"Saved {new_posts_count} new post URLs")
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        print(f"Error processing post: {str(e)}")
                        continue
                
                post_count = current_post_count
            
            # More aggressive scrolling to ensure new content loads
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))  # Longer wait to ensure content loads
            
            # Check for "End of Results" message
            try:
                end_of_results = driver.find_elements(By.XPATH, "//div[contains(text(), 'End of Results')]")
                if end_of_results:
                    print("Reached end of results")
                    break
            except:
                pass
            
            scroll_count += 1
            
            # Add a random longer pause every 10 scrolls to avoid being flagged as a bot
            if scroll_count % 10 == 0:
                time.sleep(random.uniform(5, 10))
        
        # Save progress after finishing each keyword
        all_posts_df.to_csv(OUTPUT_FILE, index=False)
        save_progress(keyword_index + 1, list(processed_urls))
        print(f"Completed keyword: {current_keyword}. Found {new_posts_count} new relevant posts.")
        
        # Random delay between keywords
        time.sleep(random.uniform(10, 20))

except Exception as e:
    print(f"Error occurred: {str(e)}")
    # Save progress before exiting
    all_posts_df.to_csv(OUTPUT_FILE, index=False)
    save_progress(last_keyword_index, list(processed_urls))  # Using processed_urls here

finally:
    # Save final results
    all_posts_df.to_csv(OUTPUT_FILE, index=False)
    save_progress(last_keyword_index, list(processed_urls))  # Using processed_urls here
    print(f"Crawling completed. Total post URLs collected: {len(all_posts_df)}")
    
    # Close the browser
    driver.quit()
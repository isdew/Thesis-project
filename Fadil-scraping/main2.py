from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import time
import random
import pandas as pd
import os
import sys
import json
from bs4 import BeautifulSoup

# Setup Chrome WebDriver with profile
CHROME_DRIVER_PATH = "/Users/fadil/Downloads/chromedriver-mac/chromedriver"
PROGRESS_FILE = "fb_crawler_progress.json"
OUTPUT_FILE = "facebook_powerbank_all_data3.csv"

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
FILTER_KEYWORDS = ["Power Bank","พาวเวอร์แบงค์","พาวเวอร์แบงก์","เพาเวอร์แบงค์","เพาเวอร์แบงก์","แบตเตอรี่สำรอง","Powerbank","แบตสำรอง","Eloop", "แบตฯ",  "พาวเวอร์",  "พาวเวอร์แบ็งค์", "พาเวอร์แบงค์", ]

# Timing parameters
PAGE_SEARCH_PAUSE_TIME = 10       # Time to wait between page search scrolls (seconds)
PAGE_SEARCH_MAX_SCROLLS = 2      # Maximum number of scrolls when searching for pages
GROUP_SEARCH_PAUSE_TIME = 10      # Time to wait between group search scrolls (seconds)
GROUP_SEARCH_MAX_SCROLLS = 2     # Maximum number of scrolls when searching for groups

POST_SCROLL_PAUSE_TIME = 3       # Time to wait between post scrolls (seconds) 
POST_SCROLL_MAX_ATTEMPTS = 2     # Maximum number of scrolls per page when looking for posts
POST_NO_CHANGE_LIMIT = 2         # Number of consecutive scrolls with no new posts before stopping

# Page load parameters
PAGE_LOAD_WAIT_TIME = 5          # Time to wait after page loads (seconds)
SAVE_PROGRESS_INTERVAL = 5        # Save progress after every X pages processed

# Marketplace parameters
MARKETPLACE_SCROLL_TIMES = 900     # Number of times to scroll in marketplace search
MARKETPLACE_PAUSE_TIME = 7        # Time to wait between marketplace scrolls (seconds)
MARKETPLACE_ITEM_WAIT_TIME = 4    # Time to wait after loading an item page (seconds)

#################################################
#           SCRIPT IMPLEMENTATION               #
#################################################

# Setup Chrome WebDriver with profile
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--user-data-dir=/Users/fadil/Library/Application Support/Google/Chrome")
chrome_options.add_argument("--profile-directory=Default")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-notifications")  # Disable Facebook notifications

# Initialize WebDriver
service = Service(CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Store extracted data
all_post_urls = set()            # Avoid duplicate posts
all_page_links = set()           # Avoid duplicate pages across ALL keywords
all_group_links = set()          # Avoid duplicate groups across ALL keywords
all_marketplace_items = set()    # Avoid duplicate marketplace items
completed_keywords = []          # Track which keywords we've already processed

# Initialize or load progress tracking
def init_progress():
    global all_post_urls, all_page_links, all_group_links, all_marketplace_items, completed_keywords
    
    if not os.path.exists(PROGRESS_FILE) or restart_mode:
        progress = {
            "completed_keywords": [],
            "page_links": [],
            "group_links": [],
            "post_urls": [],
            "marketplace_items": []
        }
        # Create the file
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
        return progress
    
    try:
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
            # Load the saved data into our variables
            all_post_urls = set(progress["post_urls"])
            all_page_links = set(progress["page_links"])
            all_group_links = set(progress.get("group_links", []))  # Handle older progress files
            all_marketplace_items = set(progress.get("marketplace_items", []))  # Handle older progress files
            completed_keywords = progress["completed_keywords"]
            return progress
    except Exception as e:
        print(f"⚠️ Error loading progress file: {e}")
        print("Creating new progress file...")
        progress = {
            "completed_keywords": [],
            "page_links": [],
            "group_links": [],
            "post_urls": [],
            "marketplace_items": []
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
        return progress

# Save progress
def save_progress():
    try:
        progress = {
            "completed_keywords": completed_keywords,
            "page_links": list(all_page_links),
            "group_links": list(all_group_links),
            "post_urls": list(all_post_urls),
            "marketplace_items": list(all_marketplace_items)
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
        
        # Combine all links into one DataFrame with type identification
        all_data = []
        
        # Add page/group posts
        for url in all_post_urls:
            if "facebook.com/groups" in url:
                source_type = "Group Post"
            else:
                source_type = "Page Post"
            all_data.append({"URL": url, "Type": source_type})
            
        # Add marketplace items
        for url in all_marketplace_items:
            all_data.append({"URL": url, "Type": "Marketplace Item"})
        
        # Save combined data to CSV
        df = pd.DataFrame(all_data)
        df.to_csv(OUTPUT_FILE, index=False)
        
        print(f"💾 Progress saved - {len(all_post_urls)} posts and {len(all_marketplace_items)} marketplace items collected so far.")
    except Exception as e:
        print(f"⚠️ Error saving progress: {e}")

# Function to search for FB pages
def find_pages_for_keyword(search_query):
    global all_page_links

    print(f"\n🔍 Searching for PAGES with keyword: {search_query}")

    search_url = f"https://www.facebook.com/search/pages/?q={search_query.replace(' ', '%20')}"
    driver.get(search_url)
    time.sleep(PAGE_LOAD_WAIT_TIME)

    previous_count = 0
    stop_scroll_attempts = 0
    new_page_links = set()

    print("📜 Scrolling to find pages...")
    for scroll_num in range(1, PAGE_SEARCH_MAX_SCROLLS + 1):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(PAGE_SEARCH_PAUSE_TIME)

        results = driver.find_elements(By.XPATH, "//div[@role='article']")
        current_count = len(results)

        print(f"📜 Page search scroll #{scroll_num} - Found {current_count} result blocks")

        if current_count == previous_count:
            stop_scroll_attempts += 1
            print(f"⚠️ No new blocks found ({stop_scroll_attempts}/{POST_NO_CHANGE_LIMIT})")
        else:
            stop_scroll_attempts = 0
            print(f"✅ Found {current_count - previous_count} new blocks")

        if stop_scroll_attempts >= POST_NO_CHANGE_LIMIT:
            print("✅ No more new results. Stopping scroll.")
            break

        previous_count = current_count

    print("🔍 Extracting valid page links from results...")
    for result in results:
        try:
            text = result.text.lower()
            if "page ·" in text or "เพจ" in text:  # "Page ·" or "เพจ" in Thai
                link_elem = result.find_element(By.XPATH, ".//a[contains(@href, 'facebook.com/') and not(contains(@href, 'profile.php'))]")
                link = link_elem.get_attribute("href")

                if link and link not in all_page_links and "groups" not in link:
                    new_page_links.add(link)
                    all_page_links.add(link)
                    print(f"🆕 NEW PAGE: {link}")
                elif link in all_page_links:
                    print(f"🔄 DUPLICATE PAGE: {link}")
        except Exception as e:
            print(f"⚠️ Error extracting page block: {e}")

    print(f"🔹 Found {len(new_page_links)} NEW Facebook pages for this keyword.")
    print(f"🔹 Total unique pages collected so far: {len(all_page_links)}")
    return new_page_links

# Function to search for FB groups
def find_groups_for_keyword(search_query):
    global all_group_links

    print(f"\n🔍 Searching for GROUPS with keyword: {search_query}")

    search_url = f"https://www.facebook.com/search/groups/?q={search_query.replace(' ', '%20')}"
    driver.get(search_url)
    time.sleep(PAGE_LOAD_WAIT_TIME)

    previous_count = 0
    stop_scroll_attempts = 0
    new_group_links = set()

    print("📜 Scrolling to find groups...")
    for scroll_num in range(1, GROUP_SEARCH_MAX_SCROLLS + 1):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(GROUP_SEARCH_PAUSE_TIME)

        results = driver.find_elements(By.XPATH, "//div[@role='article']")
        current_count = len(results)

        print(f"📜 Group search scroll #{scroll_num} - Found {current_count} result blocks")

        if current_count == previous_count:
            stop_scroll_attempts += 1
            print(f"⚠️ No new blocks found ({stop_scroll_attempts}/{POST_NO_CHANGE_LIMIT})")
        else:
            stop_scroll_attempts = 0
            print(f"✅ Found {current_count - previous_count} new blocks")

        if stop_scroll_attempts >= POST_NO_CHANGE_LIMIT:
            print("✅ No more new group results. Stopping scroll.")
            break

        previous_count = current_count

    print("🔍 Extracting valid group links from results...")
    for result in results:
        try:
            text = result.text.lower()
            if "group ·" in text or "กลุ่ม" in text:  # "Group ·" or "กลุ่ม" in Thai
                link_elem = result.find_element(By.XPATH, ".//a[contains(@href, 'facebook.com/groups/')]")
                link = link_elem.get_attribute("href")

                if link and link not in all_group_links:
                    new_group_links.add(link)
                    all_group_links.add(link)
                    print(f"🆕 NEW GROUP: {link}")
                elif link in all_group_links:
                    print(f"🔄 DUPLICATE GROUP: {link}")
        except Exception as e:
            print(f"⚠️ Error extracting group block: {e}")

    print(f"🔹 Found {len(new_group_links)} NEW Facebook groups for this keyword.")
    print(f"🔹 Total unique groups collected so far: {len(all_group_links)}")
    return new_group_links
# Function to search for marketplace items
def find_marketplace_items_for_keyword(search_query):
    """ Searches Facebook Marketplace for items with the given keyword """
    global all_marketplace_items
    
    print(f"\n🔍 Searching for MARKETPLACE items with keyword: {search_query}")

    # Create marketplace search URL
    marketplace_url = f"https://www.facebook.com/marketplace/search/?query={search_query.replace(' ', '%20')}"
    driver.get(marketplace_url)
    time.sleep(PAGE_LOAD_WAIT_TIME)  # Allow time for the page to load

    # Human-like scrolling to load more items
    print("📜 Scrolling to find marketplace items...")
    for scroll_num in range(1, MARKETPLACE_SCROLL_TIMES + 1):
        # Random scroll distance for more human-like behavior
        scroll_distance = random.randint(700, 900)
        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
        
        # Show scrolling progress
        print(f"📜 Marketplace scroll #{scroll_num}/{MARKETPLACE_SCROLL_TIMES}")
        
        # Random wait time between scrolls
        time.sleep(random.uniform(MARKETPLACE_PAUSE_TIME * 0.8, MARKETPLACE_PAUSE_TIME * 1.2))

    # Extract marketplace item links using BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.find_all("a", href=True)
    
    # Filter for marketplace items
    new_marketplace_items = set()
    for item in items:
        try:
            link = item["href"]
            if "/marketplace/item/" in link:  # Ensure it's a marketplace item
                full_link = "https://www.facebook.com" + link.split("?")[0]  # Remove tracking parameters
                
                # Check if already processed
                if full_link in all_marketplace_items:
                    print(f"🔄 DUPLICATE MARKETPLACE ITEM: {full_link}")
                else:
                    print(f"🆕 NEW MARKETPLACE ITEM: {full_link}")
                    new_marketplace_items.add(full_link)
                    all_marketplace_items.add(full_link)  # Add to global tracking set
        except Exception as e:
            print(f"⚠️ Error extracting marketplace item link: {e}")

    print(f"🔹 Found {len(new_marketplace_items)} NEW Facebook marketplace items for this keyword.")
    print(f"🔹 Total unique marketplace items collected so far: {len(all_marketplace_items)}")
    
    return new_marketplace_items

# Function to check if a group is public
def is_group_public(driver, group_link):
    """Determine if a Facebook group is public or private"""
    try:
        driver.get(group_link)
        time.sleep(PAGE_LOAD_WAIT_TIME)
        
        # Look for join button - if present, it's likely private
        join_buttons = driver.find_elements(By.XPATH, "//div[contains(text(), 'Join group')]")
        if join_buttons:
            # Check if there's any indicator this is a private group
            private_indicators = driver.find_elements(By.XPATH, "//span[contains(text(), 'Private group')]")
            if private_indicators:
                print(f"🔒 Private group detected: {group_link}")
                return False
                
        # Check if we can see posts - a sign it's public or we're already a member
        posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/posts/') or contains(@href, '/photos/')]")
        if posts:
            print(f"🌐 Public group or member of group: {group_link}")
            return True
            
        # If in doubt, try scrolling to see if content loads
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(3)
        posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/posts/') or contains(@href, '/photos/')]")
        if posts:
            print(f"🌐 Confirmed public or member group: {group_link}")
            return True
            
        print(f"🔒 Likely private group (cannot view content): {group_link}")
        return False
        
    except Exception as e:
        print(f"⚠️ Error checking group type: {e}")
        return False  # Assume private/inaccessible if there's an error

def scroll_page_and_extract_posts(source_link, source_type="page"):
    global all_post_urls

    print(f"📜 Starting to scroll {source_type} to load ALL posts...")
    previous_post_count = 0
    consecutive_no_change = 0

    for scroll_attempt in range(1, POST_SCROLL_MAX_ATTEMPTS + 1):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(POST_SCROLL_PAUSE_TIME)

        posts = driver.find_elements(By.XPATH, "//div[@role='article']")
        current_post_count = len(posts)

        if current_post_count == previous_post_count:
            consecutive_no_change += 1
            if consecutive_no_change >= POST_NO_CHANGE_LIMIT:
                print(f"✅ No new posts after {POST_NO_CHANGE_LIMIT} scrolls. Stopping.")
                break
        else:
            consecutive_no_change = 0

        previous_post_count = current_post_count

    print(f"✅ Scrolling complete. Found {len(posts)} total post blocks.")

    post_count = 0
    for post in posts:
        try:
            post_html = post.get_attribute("outerHTML").lower()
            post_text = post.text.lower() if post.text else ""

            has_image = "<img" in post_html or "background-image" in post_html
            has_keyword = any(k.lower() in post_text or k.lower() in post_html for k in FILTER_KEYWORDS)

            post_link_elem = post.find_elements(By.XPATH, ".//a[contains(@href, '/posts/') or contains(@href, '/photos/')]")
            post_url = post_link_elem[0].get_attribute("href") if post_link_elem else None

            if has_image and has_keyword and post_url and post_url not in all_post_urls:
                all_post_urls.add(post_url)
                post_count += 1
                print(f"🖼️✅ Image Post Found: {post_url}")
        except Exception as e:
            print(f"⚠️ Error reading post block: {e}")

    print(f"✅ {post_count} image posts with matching keywords extracted.")
    return post_count
# Process a keyword
def process_keyword(keyword):
    global all_post_urls, all_page_links, all_group_links, all_marketplace_items, completed_keywords
    
    print(f"\n📌 Processing keyword: {keyword}")
    
    # Store counts before this keyword
    pages_before = len(all_page_links)
    groups_before = len(all_group_links)
    posts_before = len(all_post_urls)
    marketplace_before = len(all_marketplace_items)
    
    # Step 1: Find pages for this keyword
    new_pages = find_pages_for_keyword(keyword)
    
    # Step 2: Find groups for this keyword
    new_groups = find_groups_for_keyword(keyword)
    
    # Step 3: Find marketplace items for this keyword
    new_marketplace_items = find_marketplace_items_for_keyword(keyword)
    
    # Step 4: Process each page
    print(f"\n🔍 Processing {len(new_pages)} pages for keyword: {keyword}")
    pages_processed = 0
    
    for index, page_link in enumerate(new_pages):
        try:
            print(f"🔹 Visiting PAGE {index + 1}/{len(new_pages)}: {page_link}")
            driver.get(page_link)
            time.sleep(PAGE_LOAD_WAIT_TIME)
            
            # Extract posts from this page
            scroll_page_and_extract_posts(page_link, "page")
            pages_processed += 1
            
            # Save progress periodically
            if pages_processed % SAVE_PROGRESS_INTERVAL == 0:
                save_progress()
                
        except Exception as e:
            print(f"⚠️ Error processing page {page_link}: {e}")
    
    # Step 5: Process each public group
    print(f"\n🔍 Processing {len(new_groups)} groups for keyword: {keyword}")
    groups_processed = 0
    public_groups = 0
    
    for index, group_link in enumerate(new_groups):
        try:
            print(f"🔹 Checking GROUP {index + 1}/{len(new_groups)}: {group_link}")
            
            # Check if it's a public group
            if is_group_public(driver, group_link):
                print(f"🌐 Processing PUBLIC group: {group_link}")
                scroll_page_and_extract_posts(group_link, "group")
                public_groups += 1
            else:
                print(f"🔒 Skipping PRIVATE group: {group_link}")
                
            groups_processed += 1
            
            # Save progress periodically
            if groups_processed % SAVE_PROGRESS_INTERVAL == 0:
                save_progress()
                
        except Exception as e:
            print(f"⚠️ Error processing group {group_link}: {e}")
    
    # Step 6: Process each marketplace item (just visit and verify)
    print(f"\n🔍 Verifying {len(new_marketplace_items)} marketplace items for keyword: {keyword}")
    marketplace_processed = 0
    
    for index, item_link in enumerate(new_marketplace_items):
        try:
            print(f"🔹 Verifying MARKETPLACE ITEM {index + 1}/{len(new_marketplace_items)}: {item_link}")
            driver.get(item_link)
            time.sleep(MARKETPLACE_ITEM_WAIT_TIME)
            
            # You could add additional extraction code here if needed
            # For now, we're just verifying the links are valid
            
            marketplace_processed += 1
            
            # Save progress periodically
            if marketplace_processed % SAVE_PROGRESS_INTERVAL == 0:
                save_progress()
                
        except Exception as e:
            print(f"⚠️ Error processing marketplace item {item_link}: {e}")
    
    # Calculate statistics for this keyword
    new_page_count = len(all_page_links) - pages_before
    new_group_count = len(all_group_links) - groups_before
    new_post_count = len(all_post_urls) - posts_before
    new_marketplace_count = len(all_marketplace_items) - marketplace_before
    
    print(f"\n✅ Keyword '{keyword}' complete:")
    print(f"  - Pages: {new_page_count} new (processed {pages_processed})")
    print(f"  - Groups: {new_group_count} new (processed {groups_processed}, {public_groups} public)")
    print(f"  - Posts: {new_post_count} new")
    print(f"  - Marketplace Items: {new_marketplace_count} new")
    
    # Mark this keyword as completed
    if keyword not in completed_keywords:
        completed_keywords.append(keyword)
    
    # Save progress after completing the keyword
    save_progress()
    
    return {
        "new_pages": new_page_count,
        "total_pages": len(all_page_links),
        "new_groups": new_group_count,
        "total_groups": len(all_group_links),
        "public_groups": public_groups,
        "new_posts": new_post_count,
        "total_posts": len(all_post_urls),
        "new_marketplace": new_marketplace_count,
        "total_marketplace": len(all_marketplace_items)
    }

# Main execution
if __name__ == "__main__":
    # Check for restart flag
    restart_mode = len(sys.argv) > 1 and sys.argv[1] == "--restart"
    if restart_mode:
        print("\n🔄 RESTART MODE: Starting fresh and clearing progress...")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        if os.path.exists(OUTPUT_FILE):
            backup_file = f"{OUTPUT_FILE}.bak"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(OUTPUT_FILE, backup_file)
            print(f"Previous results backed up to {backup_file}")
    else:
        print("\n▶️ RESUME MODE: Continuing from previous run...")
    
    # Dictionary to store stats for each keyword
    keyword_stats = {}
    
    try:
        # Initialize/load progress
        progress = init_progress()
        print(f"📊 Starting with {len(all_page_links)} pages, {len(all_group_links)} groups, {len(all_post_urls)} posts, {len(all_marketplace_items)} marketplace items")
        print(f"✅ Already completed keywords: {completed_keywords}")
        
        # Setup the initial output file if it doesn't exist
        if not os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'w') as f:
                f.write("URL,Type\n")
        
        # Print configuration for user reference
        print("\n⚙️ CURRENT CONFIGURATION:")
        print(f"- Page search pause time: {PAGE_SEARCH_PAUSE_TIME} seconds")
        print(f"- Page search max scrolls: {PAGE_SEARCH_MAX_SCROLLS}")
        print(f"- Group search pause time: {GROUP_SEARCH_PAUSE_TIME} seconds")
        print(f"- Group search max scrolls: {GROUP_SEARCH_MAX_SCROLLS}")
        print(f"- Post scroll pause time: {POST_SCROLL_PAUSE_TIME} seconds")
        print(f"- Post scroll max attempts: {POST_SCROLL_MAX_ATTEMPTS}")
        print(f"- Post no-change limit: {POST_NO_CHANGE_LIMIT}")
        print(f"- Page load wait time: {PAGE_LOAD_WAIT_TIME} seconds")
        print(f"- Marketplace scroll times: {MARKETPLACE_SCROLL_TIMES}")
        print(f"- Marketplace pause time: {MARKETPLACE_PAUSE_TIME} seconds")
        print(f"- Save progress interval: Every {SAVE_PROGRESS_INTERVAL} items")
        
        # Process each keyword
        for i, keyword in enumerate(SEARCH_KEYWORDS):
            # Skip already completed keywords unless in restart mode
            if keyword in completed_keywords and not restart_mode:
                print(f"\n⏭️ Skipping already completed keyword: {keyword}")
                continue
                
            print(f"\n📌 Processing keyword {i+1}/{len(SEARCH_KEYWORDS)}: {keyword}")
            
            # Process the keyword (find and crawl pages, groups, and marketplace)
            stats = process_keyword(keyword)
            keyword_stats[keyword] = stats
            
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        # Save progress even if there's an error
        save_progress()
    finally:
        # Print summary statistics
        print("\n📈 CRAWLING RESULTS 📈")
        print("-" * 140)
        print(f"{'KEYWORD':<20} {'NEW PAGES':<10} {'NEW GROUPS':<10} {'PUBLIC GRPS':<10} {'NEW POSTS':<10} {'NEW MARKET':<10} {'TOTAL PAGES':<10} {'TOTAL GROUPS':<10} {'TOTAL POSTS':<10} {'TOTAL MARKET':<10}")
        print("-" * 140)
        
        running_total_pages = 0
        running_total_groups = 0
        running_total_posts = 0
        running_total_marketplace = 0
        
        for keyword, stats in keyword_stats.items():
            running_total_pages += stats["new_pages"]
            running_total_groups += stats["new_groups"]
            running_total_posts += stats["new_posts"]
            running_total_marketplace += stats.get("new_marketplace", 0)
            
            print(f"{keyword:<20} {stats['new_pages']:<10} {stats['new_groups']:<10} {stats.get('public_groups', 0):<10} " +
                  f"{stats['new_posts']:<10} {stats.get('new_marketplace', 0):<10} {running_total_pages:<10} " +
                  f"{running_total_groups:<10} {running_total_posts:<10} {running_total_marketplace:<10}")
        
        print("-" * 140)
        print(f"{'GRAND TOTAL':<20} {len(all_page_links):<10} {len(all_group_links):<10} {'':<10} {len(all_post_urls):<10} {len(all_marketplace_items):<10}")

        print("\n🎉 Crawling completed!")
        print(f"📊 Final Statistics: Processed {len(all_page_links)} pages, {len(all_group_links)} groups, and found {len(all_post_urls)} relevant posts and {len(all_marketplace_items)} marketplace items.")
        print(f"💾 All data saved to '{OUTPUT_FILE}'.")

        # Close the browser
        driver.quit()
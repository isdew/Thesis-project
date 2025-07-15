import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import random
import time

from oauth2client.service_account import ServiceAccountCredentials
import gspread


# --- SETUP SELENIUM ---
chrome_driver_path = "/Users/fadil/Downloads/chromedriver-mac/chromedriver"
chrome_options = Options()
chrome_options.add_argument("--user-data-dir=/Users/fadil/Library/Application Support/Google/Chrome")
chrome_options.add_argument("--profile-directory=Default")
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)


# --- SETUP GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open your Google Sheet
spreadsheet = client.open("Facebook Image URLs")  # Change to your sheet name
worksheet = spreadsheet.sheet1  # Use the first sheet

def human_delay(min_time=2, max_time=5):
    """Waits for a random time between actions to mimic human behavior."""
    delay = random.uniform(min_time, max_time)
    time.sleep(delay)

# Scroll to load more posts
def human_scroll(driver, times=5):
    """Scrolls randomly like a human user to load more posts."""
    for _ in range(times):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)

# --- SCRAPING FACEBOOK ---
driver.execute_script("window.open('https://www.facebook.com/bebephone.online','_blank');")
human_delay(3, 6)
driver.switch_to.window(driver.window_handles[-1])
print("Switched to new tab.")
human_scroll(driver, 5)

# Keywords to search for in posts
keywords = ["power bank", "พาวเวอร์แบงค์"]

# Find posts
post_containers = driver.find_elements(By.XPATH, "//div[contains(@role,'article')]")
print(f"Found {len(post_containers)} posts!")

# Store results in a list before bulk uploading to Google Sheets
data_to_upload = []

for index, post in enumerate(post_containers):
    try:
        post_text = post.text.lower()

        # Extract post link
        try:
            post_link = post.find_element(By.XPATH, ".//a[contains(@href, '/posts/')]").get_attribute("href")
        except:
            post_link = "No_Link_Found"

        print(f"\n**Post {index + 1}:** \n{post_text[:200]}...")
        print(f" Post Link: {post_link}")

        if any(keyword in post_text for keyword in keywords):
            print("**Keyword Detected! Extracting post image URLs...**")

            # Find images in the post
            images = post.find_elements(By.XPATH, ".//img")
            image_urls = []

            for idx, img in enumerate(images):
                img_url = img.get_attribute("src")

                # Skip profile pictures, emojis, etc.
                if img_url and "profile" not in img_url and "emoji" not in img_url and "sticker" not in img_url:
                    print(f"Image {idx + 1} URL: {img_url}")
                    image_urls.append(img_url)

                    # Append (Post URL, Image URL) to list
                    data_to_upload.append([post_link, img_url])

    except Exception as e:
        print(f"Error processing post: {e}")

# --- UPLOAD TO GOOGLE SHEETS ---
if data_to_upload:
    worksheet.append_rows(data_to_upload)
    print(f"\nUploaded {len(data_to_upload)} entries to Google Sheets!")
else:
    print("\nNo matching posts found!")


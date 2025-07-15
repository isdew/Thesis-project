# Simple Chrome Test - Manual ChromeDriver
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def test_chrome():
    print("🧪 Simple Chrome Test")
    print("=" * 30)
    
    # Kill existing Chrome
    os.system("pkill -f 'Google Chrome'")
    os.system("pkill -f 'chromedriver'")
    time.sleep(3)
    
    # ดาวน์โหลด ChromeDriver ด้วยตนเอง
    print("📋 Chrome version check:")
    os.system("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --version")
    
    print("\n💡 Manual ChromeDriver setup:")
    print("1. Go to: https://googlechromelabs.github.io/chrome-for-testing/")
    print("2. Download ChromeDriver for your Chrome version")
    print("3. Put chromedriver in /usr/local/bin/ or update path below")
    
    # ใส่ path ของ ChromeDriver ที่ดาวน์โหลดมา
    chromedriver_path = input("\nEnter ChromeDriver path (or press Enter for /usr/local/bin/chromedriver): ").strip()
    if not chromedriver_path:
        chromedriver_path = "/usr/local/bin/chromedriver"
    
    if not os.path.exists(chromedriver_path):
        print(f"❌ ChromeDriver not found at: {chromedriver_path}")
        return
    
    # Chrome settings
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9223")  # ใช้ port อื่น
    chrome_options.add_argument("--user-data-dir=/Users/fadil/Library/Application Support/Google/Chrome")
    chrome_options.add_argument("--profile-directory=Default")
    
    try:
        print(f"🚀 Starting Chrome with: {chromedriver_path}")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Chrome started!")
        time.sleep(2)
        
        # Test basic navigation
        print("🔄 Testing navigation...")
        driver.get("https://www.google.com")
        time.sleep(3)
        
        print(f"📍 Current URL: {driver.current_url}")
        print(f"📝 Title: {driver.title}")
        
        if "google.com" in driver.current_url:
            print("✅ Basic navigation works!")
            
            # Now try Facebook
            print("\n🔄 Trying Facebook...")
            driver.get("https://www.facebook.com")
            time.sleep(5)
            
            print(f"📍 Facebook URL: {driver.current_url}")
            print(f"📝 Facebook Title: {driver.title}")
            
            if "facebook.com" in driver.current_url:
                print("🎉 SUCCESS! Facebook works!")
            else:
                print("❌ Facebook navigation failed")
        else:
            print("❌ Basic navigation failed")
        
        input("\n⏸️  Press Enter to close browser...")
        driver.quit()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_chrome()
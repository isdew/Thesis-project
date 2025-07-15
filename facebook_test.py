# Firefox Facebook Test - ใช้ Firefox แทน Chrome
import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager

def test_facebook_firefox():
    print("🦊 Firefox Facebook Test with Profile")
    print("=" * 40)
    
    # Kill existing Firefox
    os.system("pkill -f Firefox")
    time.sleep(3)
    
    # หา Firefox profiles
    firefox_profile_dir = "/Users/fadil/Library/Application Support/Firefox/Profiles"
    
    print("🔍 Looking for Firefox profiles...")
    try:
        profiles = [d for d in os.listdir(firefox_profile_dir) if os.path.isdir(os.path.join(firefox_profile_dir, d))]
        print("📋 Available Firefox profiles:")
        for i, profile in enumerate(profiles):
            print(f"   {i+1}. {profile}")
        
        if not profiles:
            print("❌ No Firefox profiles found!")
            return
            
        # ให้เลือก profile หรือใช้ profile แรก
        choice = input(f"\nSelect profile (1-{len(profiles)}) or Enter for first profile: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(profiles):
            selected_profile = profiles[int(choice)-1]
        else:
            selected_profile = profiles[0]
            
        profile_path = os.path.join(firefox_profile_dir, selected_profile)
        print(f"✅ Using profile: {selected_profile}")
        print(f"📁 Profile path: {profile_path}")
        
    except Exception as e:
        print(f"❌ Error finding profiles: {e}")
        return
    
    # Firefox settings with profile
    firefox_options = webdriver.FirefoxOptions()
    firefox_options.add_argument("--width=1200")
    firefox_options.add_argument("--height=800")
    
    # ใช้ profile ที่มี Facebook login
    firefox_options.add_argument("-profile")
    firefox_options.add_argument(profile_path)
    
    try:
        print("📦 Starting Firefox with existing profile...")
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        print("✅ Firefox started successfully with profile")
        driver.maximize_window()
        time.sleep(3)
        
        # แสดงข้อมูลเริ่มต้น
        print(f"🔍 Initial URL: {driver.current_url}")
        print(f"🔍 Initial Title: {driver.title}")
        
        # ทดสอบไป Facebook
        print("🔄 Navigating to Facebook...")
        driver.get("https://www.facebook.com")
        time.sleep(8)  # รอนานขึ้นเพื่อให้ profile โหลด
        
        current_url = driver.current_url
        title = driver.title
        
        print(f"📍 Facebook URL: {current_url}")
        print(f"📝 Facebook Title: {title}")
        
        if "facebook.com" in current_url:
            print("✅ SUCCESS - Reached Facebook!")
            
            # ตรวจสอบสถานะ login อย่างละเอียด
            try:
                print("🔍 Checking login status...")
                
                # หา elements ต่างๆ
                marketplace_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/marketplace')]")
                login_forms = driver.find_elements(By.XPATH, "//input[@type='email']")
                password_forms = driver.find_elements(By.XPATH, "//input[@type='password']")
                profile_elements = driver.find_elements(By.XPATH, "//div[@role='banner']")
                
                print(f"🛍️  Marketplace links: {len(marketplace_links)}")
                print(f"📧 Email inputs: {len(login_forms)}")
                print(f"🔒 Password inputs: {len(password_forms)}")
                print(f"🏠 Profile elements: {len(profile_elements)}")
                
                if marketplace_links:
                    print("🎯 Status: LOGGED IN (found marketplace)")
                    
                    # ลองไป marketplace
                    print("🛍️  Testing marketplace navigation...")
                    driver.get("https://www.facebook.com/marketplace")
                    time.sleep(5)
                    
                    marketplace_url = driver.current_url
                    print(f"📍 Marketplace URL: {marketplace_url}")
                    
                    if "marketplace" in marketplace_url:
                        print("✅ MARKETPLACE SUCCESS!")
                        
                        # หา search box
                        search_boxes = driver.find_elements(By.XPATH, "//input[@placeholder='Search Marketplace' or @placeholder='ค้นหาใน Marketplace']")
                        print(f"🔍 Search boxes found: {len(search_boxes)}")
                        
                        if search_boxes:
                            print("🎉 READY FOR SCRAPING!")
                        else:
                            print("⚠️  No search box found")
                    else:
                        print("❌ Could not access marketplace")
                        
                elif login_forms and password_forms:
                    print("🔑 Status: NEED LOGIN (found login form)")
                    print("💡 Please login manually in Firefox first")
                    
                else:
                    print("❓ Status: UNKNOWN")
                    
                    # แสดงเนื้อหาบางส่วน
                    try:
                        body_text = driver.find_element(By.TAG_NAME, "body").text[:300]
                        print(f"📄 Page content: {body_text}")
                    except:
                        pass
                    
            except Exception as e:
                print(f"⚠️  Could not check status: {e}")
                
        else:
            print("❌ FAILED - Did not reach Facebook")
            print(f"Got redirected to: {current_url}")
            
        # Page source length
        page_length = len(driver.page_source)
        print(f"📄 Page content length: {page_length} characters")
        
        input("\n⏸️  Press Enter to close Firefox...")
        driver.quit()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure Firefox is installed and profile exists")

if __name__ == "__main__":
    test_facebook_firefox()
#imports here
import time
import random
import time

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
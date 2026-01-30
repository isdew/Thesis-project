"""
Example: How to integrate ProductConfig into your scraper

This shows the key changes needed to make your scraper work with
the product configuration system.
"""

from product_config import ProductConfig

# ==================== BEFORE (hardcoded) ====================
# KEYWORDS = ["Power bank", "พาวเวอร์แบงค์", "PowerBank", ...]
# FILTER_KEYWORDS = ["Power bank", "พาวเวอร์แบงค์", ...]
# FILTER_KEYWORDS_LOWER = {k.lower() for k in FILTER_KEYWORDS}


# ==================== AFTER (configurable) ====================

# Load configuration
config = ProductConfig()

# Select product (this will come from frontend later)
SELECTED_PRODUCT = "power_bank"  # or "adapter", "usb_cable", etc.

# Get keywords dynamically
KEYWORDS = config.get_keywords(SELECTED_PRODUCT)
FILTER_KEYWORDS = config.get_filter_keywords(SELECTED_PRODUCT)
FILTER_KEYWORDS_LOWER = config.get_filter_keywords_lower(SELECTED_PRODUCT)

# Optional: Create product-specific output directories
import os
PRODUCT_NAME = config.get_product_names()[SELECTED_PRODUCT]
CSV_FILE = f"Scrape_Data/{SELECTED_PRODUCT}/marketplace_data.csv"
SKIPPED_CSV = f"Scrape_Data/{SELECTED_PRODUCT}/skipped_posts.csv"
IMAGE_DIR = f"Scrape_Data/{SELECTED_PRODUCT}/images"


# ==================== For Frontend Integration ====================

def get_available_products() -> dict:
    """
    API endpoint for frontend to get list of products.
    Returns: {"power_bank": "Power Bank", "adapter": "Adapter / Charger", ...}
    """
    return config.get_product_names()


def run_scraper_for_product(product_id: str):
    """
    Main entry point for frontend to trigger scraping.
    """
    if product_id not in config.get_product_ids():
        raise ValueError(f"Invalid product: {product_id}")
    
    keywords = config.get_keywords(product_id)
    filter_keywords_lower = config.get_filter_keywords_lower(product_id)
    
    # ... rest of your scraper logic using these keywords
    print(f"Starting scraper for: {config.get_product_names()[product_id]}")
    print(f"Using keywords: {keywords}")


# ==================== Demo ====================
if __name__ == "__main__":
    print("Available products for frontend:")
    for pid, name in get_available_products().items():
        print(f"  - {pid}: {name}")
    
    print("\n" + "=" * 50)
    print("Testing product selection:")
    print("=" * 50)
    
    for product_id in ["power_bank", "adapter", "usb_cable"]:
        print(f"\n📦 Product: {product_id}")
        print(f"   Keywords: {config.get_keywords(product_id)}")
        print(f"   Filter (lowercase): {config.get_filter_keywords_lower(product_id)}")

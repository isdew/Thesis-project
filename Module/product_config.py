"""
Product Configuration Manager
Handles loading and accessing product definitions for the TIS scraper.
"""

import json
import os
from typing import List, Dict, Optional

CONFIG_FILE = "products_config.json"


class ProductConfig:
    """Manages product configurations for scraping."""
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.products: Dict = {}
        self.metadata: Dict = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.products = data.get("products", {})
        self.metadata = data.get("metadata", {})
    
    def reload(self) -> None:
        """Reload configuration from file (useful if config was updated)."""
        self._load_config()
    
    def get_product_ids(self) -> List[str]:
        """Get list of all available product IDs."""
        return list(self.products.keys())
    
    def get_product_names(self) -> Dict[str, str]:
        """Get mapping of product_id -> display_name."""
        return {
            pid: pdata.get("display_name", pid)
            for pid, pdata in self.products.items()
        }
    
    def get_keywords(self, product_id: str) -> List[str]:
        """Get search keywords for a product."""
        if product_id not in self.products:
            raise ValueError(f"Unknown product: {product_id}")
        return self.products[product_id].get("keywords", [])
    
    def get_filter_keywords(self, product_id: str) -> List[str]:
        """Get filter keywords for a product."""
        if product_id not in self.products:
            raise ValueError(f"Unknown product: {product_id}")
        return self.products[product_id].get("filter_keywords", [])
    
    def get_filter_keywords_lower(self, product_id: str) -> set:
        """Get filter keywords as lowercase set (for matching)."""
        return {k.lower() for k in self.get_filter_keywords(product_id)}
    
    def add_product(self, product_id: str, display_name: str, 
                    keywords: List[str], filter_keywords: List[str]) -> None:
        """Add a new product to the configuration."""
        self.products[product_id] = {
            "display_name": display_name,
            "keywords": keywords,
            "filter_keywords": filter_keywords
        }
        self._save_config()
    
    def update_product(self, product_id: str, 
                       display_name: Optional[str] = None,
                       keywords: Optional[List[str]] = None, 
                       filter_keywords: Optional[List[str]] = None) -> None:
        """Update an existing product's configuration."""
        if product_id not in self.products:
            raise ValueError(f"Unknown product: {product_id}")
        
        if display_name is not None:
            self.products[product_id]["display_name"] = display_name
        if keywords is not None:
            self.products[product_id]["keywords"] = keywords
        if filter_keywords is not None:
            self.products[product_id]["filter_keywords"] = filter_keywords
        
        self._save_config()
    
    def remove_product(self, product_id: str) -> None:
        """Remove a product from the configuration."""
        if product_id in self.products:
            del self.products[product_id]
            self._save_config()
    
    def _save_config(self) -> None:
        """Save current configuration to JSON file."""
        data = {
            "products": self.products,
            "metadata": self.metadata
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# Convenience function for quick access
def load_product_config(config_path: str = CONFIG_FILE) -> ProductConfig:
    """Load and return ProductConfig instance."""
    return ProductConfig(config_path)


# Example usage / CLI for testing
if __name__ == "__main__":
    config = ProductConfig()
    
    print("=" * 50)
    print("Available Products:")
    print("=" * 50)
    
    for pid, name in config.get_product_names().items():
        print(f"\n📦 {name} (id: {pid})")
        print(f"   Keywords: {config.get_keywords(pid)}")
        print(f"   Filter Keywords: {config.get_filter_keywords(pid)}")

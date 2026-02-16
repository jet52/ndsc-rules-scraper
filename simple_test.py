#!/usr/bin/env python3
"""
Simple test script for ND Court Rules Scraper.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from scraper.nd_courts_scraper import NDCourtsScraper
        print("✅ NDCourtsScraper imported successfully")
    except Exception as e:
        print(f"❌ Failed to import NDCourtsScraper: {e}")
        return False
    
    try:
        from utils.logger import get_logger
        print("✅ Logger imported successfully")
    except Exception as e:
        print(f"❌ Failed to import logger: {e}")
        return False
    
    try:
        from utils.file_utils import FileManager
        print("✅ FileManager imported successfully")
    except Exception as e:
        print(f"❌ Failed to import FileManager: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        import yaml
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        print("✅ Configuration loaded successfully")
        print(f"   Categories: {len(config.get('rule_categories', []))}")
        print(f"   Request delay: {config.get('scraping', {}).get('request_delay', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False

def test_scraper_initialization():
    """Test scraper initialization."""
    print("\nTesting scraper initialization...")
    
    try:
        from scraper.nd_courts_scraper import NDCourtsScraper
        scraper = NDCourtsScraper("config.yaml", verbose=True)
        print("✅ Scraper initialized successfully")
        
        # Test statistics
        stats = scraper.get_scraping_statistics()
        print(f"   Initial stats: {stats}")
        
        scraper.cleanup()
        return True
    except Exception as e:
        print(f"❌ Failed to initialize scraper: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Simple ND Court Rules Scraper Test")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test configuration
    if not test_config():
        print("\n❌ Configuration test failed")
        return False
    
    # Test scraper initialization
    if not test_scraper_initialization():
        print("\n❌ Scraper initialization test failed")
        return False
    
    print("\n✅ All basic tests passed!")
    print("\nReady to run full scrape test...")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
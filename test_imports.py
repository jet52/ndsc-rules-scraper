#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing Imports")
    print("=" * 50)
    
    # Test basic imports
    try:
        import yaml
        print("✅ PyYAML imported successfully")
    except ImportError as e:
        print(f"❌ PyYAML import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup imported successfully")
    except ImportError as e:
        print(f"❌ BeautifulSoup import failed: {e}")
        return False
    
    try:
        import lxml
        print("✅ lxml imported successfully")
    except ImportError as e:
        print(f"❌ lxml import failed: {e}")
        return False
    
    try:
        from retrying import retry
        print("✅ retrying imported successfully")
    except ImportError as e:
        print(f"❌ retrying import failed: {e}")
        return False
    
    try:
        from tqdm import tqdm
        print("✅ tqdm imported successfully")
    except ImportError as e:
        print(f"❌ tqdm import failed: {e}")
        return False
    
    # Test our custom modules
    try:
        from utils.logger import ScraperLogger
        print("✅ ScraperLogger imported successfully")
    except ImportError as e:
        print(f"❌ ScraperLogger import failed: {e}")
        return False
    
    try:
        from utils.file_utils import FileManager
        print("✅ FileManager imported successfully")
    except ImportError as e:
        print(f"❌ FileManager import failed: {e}")
        return False
    
    try:
        from scraper.citation_extractor import CitationExtractor
        print("✅ CitationExtractor imported successfully")
    except ImportError as e:
        print(f"❌ CitationExtractor import failed: {e}")
        return False
    
    try:
        from scraper.rule_parser import RuleParser
        print("✅ RuleParser imported successfully")
    except ImportError as e:
        print(f"❌ RuleParser import failed: {e}")
        return False
    
    try:
        from scraper.nd_courts_scraper import NDCourtsScraper
        print("✅ NDCourtsScraper imported successfully")
    except ImportError as e:
        print(f"❌ NDCourtsScraper import failed: {e}")
        return False
    
    return True

def test_config_loading():
    """Test that config can be loaded."""
    print("\n🧪 Testing Config Loading")
    print("=" * 50)
    
    try:
        import yaml
        with open("config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        required_keys = ['scraping', 'rule_categories', 'output', 'json_schema']
        for key in required_keys:
            if key in config:
                print(f"✅ Config key '{key}' found")
            else:
                print(f"❌ Config key '{key}' missing")
                return False
        
        print("✅ Config loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 ND Court Rules Scraper - Import Test")
    print("=" * 60)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed!")
        return False
    
    # Test config loading
    if not test_config_loading():
        print("\n❌ Config loading failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed!")
    print("\nNext steps:")
    print("1. Run the scraper: python src/main.py --verbose --categories 'Appellate Procedure' 'Administrative Rules'")
    print("2. Run full validation: python test_scraper.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
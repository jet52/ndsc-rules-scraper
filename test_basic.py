#!/usr/bin/env python3
"""
Basic test script that tests imports and basic functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_imports():
    """Test basic imports without requests."""
    print("🧪 Testing Basic Imports")
    print("=" * 50)
    
    # Test basic imports
    try:
        import yaml
        print("✅ PyYAML imported successfully")
    except ImportError as e:
        print(f"❌ PyYAML import failed: {e}")
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
    
    return True

def test_custom_modules():
    """Test our custom modules."""
    print("\n🧪 Testing Custom Modules")
    print("=" * 50)
    
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
    
    return True

def test_requests_separately():
    """Test requests separately to isolate the issue."""
    print("\n🧪 Testing Requests Separately")
    print("=" * 50)
    
    try:
        import requests
        print("✅ Requests imported successfully")
        
        # Try a simple request
        try:
            response = requests.get('https://httpbin.org/get', timeout=5)
            print(f"✅ Requests HTTP test successful: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Requests HTTP test failed: {e}")
            print("This might be due to SSL certificate issues.")
        
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
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
        
        required_keys = ['scraping', 'rule_categories', 'output']
        for key in required_keys:
            if key in config:
                print(f"✅ Config key '{key}' found")
            else:
                print(f"❌ Config key '{key}' missing")
                return False
        
        # Check for nested json_schema
        if 'output' in config and 'json_schema' in config['output']:
            print("✅ Config key 'output.json_schema' found")
        else:
            print("❌ Config key 'output.json_schema' missing")
            return False
        
        print("✅ Config loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 ND Court Rules Scraper - Basic Test")
    print("=" * 60)
    
    # Test basic imports
    if not test_basic_imports():
        print("\n❌ Basic import tests failed!")
        return False
    
    # Test custom modules
    if not test_custom_modules():
        print("\n❌ Custom module tests failed!")
        return False
    
    # Test requests separately
    if not test_requests_separately():
        print("\n❌ Requests test failed!")
        return False
    
    # Test config loading
    if not test_config_loading():
        print("\n❌ Config loading failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All basic tests passed!")
    print("\nNext steps:")
    print("1. If requests HTTP test failed, try: python -m pip install --upgrade certifi")
    print("2. Run the scraper: python src/main.py --verbose --categories 'Appellate Procedure'")
    print("3. Run full validation: python test_scraper.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
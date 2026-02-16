#!/usr/bin/env python3
"""
Simple script to test the scraper with SSL issues bypassed.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Disable SSL warnings and verification
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set environment variable to disable SSL verification
os.environ['PYTHONHTTPSVERIFY'] = '0'

def test_requests_with_ssl_bypass():
    """Test requests with SSL verification disabled."""
    print("🧪 Testing Requests with SSL Bypass")
    print("=" * 50)
    
    try:
        import requests
        print("✅ Requests imported successfully")
        
        # Try a simple request with SSL verification disabled
        try:
            response = requests.get('https://httpbin.org/get', timeout=5, verify=False)
            print(f"✅ Requests HTTP test successful: {response.status_code}")
            return True
        except Exception as e:
            print(f"❌ Requests HTTP test failed: {e}")
            return False
        
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False

def test_scraper_initialization():
    """Test scraper initialization with SSL bypass."""
    print("\n🧪 Testing Scraper Initialization")
    print("=" * 50)
    
    try:
        from scraper.nd_courts_scraper import NDCourtsScraper
        print("✅ NDCourtsScraper imported successfully")
        
        # Initialize scraper
        scraper = NDCourtsScraper(verbose=True)
        print("✅ Scraper initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Scraper initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🧪 ND Court Rules Scraper - SSL Bypass Test")
    print("=" * 60)
    
    # Test requests with SSL bypass
    if not test_requests_with_ssl_bypass():
        print("\n❌ Requests test failed!")
        return False
    
    # Test scraper initialization
    if not test_scraper_initialization():
        print("\n❌ Scraper initialization failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All SSL bypass tests passed!")
    print("\nNext steps:")
    print("1. Run the scraper: python run_scraper.py")
    print("2. Or run with main: python src/main.py --verbose --categories 'Appellate Procedure'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
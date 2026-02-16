#!/usr/bin/env python3
"""
Simple script to run the ND Court Rules scraper with SSL issues bypassed.
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

def main():
    """Run the scraper with SSL issues bypassed."""
    print("🚀 ND Court Rules Scraper - SSL Bypass Mode")
    print("=" * 60)
    
    try:
        # Import and run the scraper
        from scraper.nd_courts_scraper import NDCourtsScraper
        
        # Initialize scraper
        scraper = NDCourtsScraper(verbose=True)
        
        # Test with minimal categories
        print("\n📋 Testing with Appellate Procedure rules...")
        
        # Override config to test only one category
        test_config = {
            'rule_categories': ['Appellate Procedure'],
            'scraping': {
                'base_url': 'https://www.ndcourts.gov/legal-resources/rules',
                'request_delay': 0.3,
                'timeout': 30,
                'user_agent': 'ND-Court-Rules-Scraper/1.0'
            },
            'output': {
                'json_schema': {
                    'include_plain_text': True,
                    'include_structured_content': True,
                    'max_section_depth': 4,
                    'single_file_output': True
                }
            }
        }
        
        # Run the scraper
        results = scraper.scrape_all_rules()
        
        print(f"\n✅ Scraping completed!")
        print(f"📊 Statistics: {scraper.get_scraping_statistics()}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error running scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
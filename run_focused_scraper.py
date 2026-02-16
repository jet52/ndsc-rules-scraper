#!/usr/bin/env python3
"""
Run the updated scraper with focused parser and no rate limiting.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.nd_courts_scraper import NDCourtsScraper

def main():
    """Run the focused scraper."""
    print("🚀 Running Focused ND Court Rules Scraper")
    print("=" * 60)
    print("✅ Using FocusedRuleParser (essential metadata only)")
    print("✅ No rate limiting (maximum speed)")
    print("✅ Targeting: Appellate Procedure & Administrative Rules")
    print("=" * 60)
    
    try:
        # Initialize scraper with verbose logging
        scraper = NDCourtsScraper(config_path="config.yaml", verbose=True)
        
        # Run the scraping
        print("\n📋 Starting scraping process...")
        results = scraper.scrape_all_rules()
        
        if results["success"]:
            print("\n✅ Scraping completed successfully!")
            
            # Show statistics
            stats = results["statistics"]
            print(f"\n📊 Scraping Statistics:")
            print(f"   Total rules scraped: {stats['total_rules_scraped']}")
            print(f"   Successful rules: {stats['successful_rules']}")
            print(f"   Failed rules: {stats['failed_rules']}")
            print(f"   Categories processed: {stats['categories_processed']}")
            
            if stats['start_time'] and stats['end_time']:
                duration = stats['end_time'] - stats['start_time']
                print(f"   Duration: {duration:.2f} seconds")
                if stats['total_rules_scraped'] > 0:
                    avg_time = duration / stats['total_rules_scraped']
                    print(f"   Average time per rule: {avg_time:.2f} seconds")
            
            print(f"\n📁 Output saved to: data/processed/nd_court_rules_complete.json")
            print(f"📁 Raw HTML saved to: data/raw/")
            print(f"📁 Metadata saved to: data/metadata/")
            
            return True
        else:
            print(f"\n❌ Scraping failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running scraper: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Focused scraper completed successfully!")
        print("\nNext steps:")
        print("1. Validate the output with simple_validation.py")
        print("2. Prepare data for Claude proofreading")
    else:
        print("\n💥 Focused scraper failed!")
        sys.exit(1) 
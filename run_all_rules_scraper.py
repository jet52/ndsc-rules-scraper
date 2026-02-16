#!/usr/bin/env python3
"""
Run the scraper against ALL rule categories on the ND Courts website.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.nd_courts_scraper import NDCourtsScraper

def main():
    """Run the scraper against all rule categories."""
    print("🚀 Running Complete ND Court Rules Scraper")
    print("=" * 70)
    print("✅ Using FocusedRuleParser (essential metadata only)")
    print("✅ No rate limiting (maximum speed)")
    print("✅ Targeting ALL rule categories (20 categories)")
    print("=" * 70)
    
    try:
        # Initialize scraper with verbose logging and all rules config
        scraper = NDCourtsScraper(config_path="config_all_rules.yaml", verbose=True)
        
        # Run the scraping
        print("\n📋 Starting comprehensive scraping process...")
        print("This will scrape ALL rule categories from the ND Courts website.")
        print("Estimated time: 10-20 minutes depending on number of rules...")
        
        results = scraper.scrape_all_rules()
        
        if results["success"]:
            print("\n✅ Comprehensive scraping completed successfully!")
            
            # Show statistics
            stats = results["statistics"]
            print(f"\n📊 Comprehensive Scraping Statistics:")
            print(f"   Total rules scraped: {stats['total_rules_scraped']}")
            print(f"   Successful rules: {stats['successful_rules']}")
            print(f"   Failed rules: {stats['failed_rules']}")
            print(f"   Categories processed: {stats['categories_processed']}")
            
            if stats['start_time'] and stats['end_time']:
                duration = stats['end_time'] - stats['start_time']
                print(f"   Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
                if stats['total_rules_scraped'] > 0:
                    avg_time = duration / stats['total_rules_scraped']
                    print(f"   Average time per rule: {avg_time:.2f} seconds")
            
            print(f"\n📁 Output saved to: data/processed/nd_court_rules_complete.json")
            print(f"📁 Raw HTML saved to: data/raw/")
            print(f"📁 Metadata saved to: data/metadata/")
            
            # Show success rate
            if stats['total_rules_scraped'] > 0:
                success_rate = (stats['successful_rules'] / stats['total_rules_scraped']) * 100
                print(f"\n📈 Success Rate: {success_rate:.1f}%")
            
            return True
        else:
            print(f"\n❌ Comprehensive scraping failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running comprehensive scraper: {e}")
        return False

if __name__ == "__main__":
    print("⚠️  WARNING: This will scrape ALL rule categories from the ND Courts website.")
    print("This may take 10-20 minutes and will make many HTTP requests.")
    print("Make sure you have permission and stable internet connection.")
    
    response = input("\nDo you want to proceed? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        success = main()
        if success:
            print("\n🎉 Comprehensive scraper completed successfully!")
            print("\nNext steps:")
            print("1. Validate the output with validate_output.py")
            print("2. Review the comprehensive rule set")
            print("3. Prepare data for Claude proofreading")
        else:
            print("\n💥 Comprehensive scraper failed!")
            sys.exit(1)
    else:
        print("\n❌ Scraping cancelled by user.")
        sys.exit(0) 
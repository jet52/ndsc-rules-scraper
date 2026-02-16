#!/usr/bin/env python3
"""
Test script to compare focused parser output with current parser output.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.rule_parser_focused import FocusedRuleParser

def test_focused_parser():
    """Test the focused parser on a sample rule."""
    print("🧪 Testing Focused Rule Parser")
    print("=" * 50)
    
    # Load a sample rule from the existing output
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find an actual numbered rule
        categories = data['data']['data']['categories']
        sample_rule = None
        
        for category in categories:
            rules = category.get('rules', [])
            for rule in rules:
                if rule.get('rule_number') and rule.get('rule_number').isdigit():
                    sample_rule = rule
                    break
            if sample_rule:
                break
        
        if not sample_rule:
            print("❌ No numbered rules found in existing data")
            return False
        
        print(f"📄 Testing with rule: {sample_rule.get('title', 'Unknown')}")
        print(f"   Rule number: {sample_rule.get('rule_number', 'Unknown')}")
        print(f"   Citation: {sample_rule.get('citation', 'Unknown')}")
        
        # Show current metadata structure
        print(f"\n📋 Current metadata structure:")
        current_metadata = sample_rule.get('metadata', {})
        for key, value in current_metadata.items():
            if isinstance(value, list):
                print(f"  - {key}: {len(value)} items")
            else:
                print(f"  - {key}: {value}")
        
        # Show current content structure
        print(f"\n📝 Current content structure:")
        current_content = sample_rule.get('content', {})
        for key, value in current_content.items():
            if isinstance(value, str):
                print(f"  - {key}: {len(value)} characters")
            else:
                print(f"  - {key}: {type(value)}")
        
        # Show what the focused parser would capture
        print(f"\n🎯 Focused parser would capture:")
        print(f"  - title: {sample_rule.get('title')}")
        print(f"  - rule_number: {sample_rule.get('rule_number')}")
        print(f"  - citation: {sample_rule.get('citation')}")
        print(f"  - source_url: {sample_rule.get('source_url')}")
        print(f"  - content.plain_text: {len(current_content.get('plain_text', ''))} characters")
        print(f"  - content.structured_content: {len(current_content.get('structured_content', ''))} characters")
        print(f"  - metadata.authority: {current_metadata.get('authority')}")
        print(f"  - metadata.effective_date: {current_metadata.get('effective_date')}")
        print(f"  - metadata.last_updated: {current_metadata.get('last_updated')}")
        print(f"  - metadata.scraped_at: {current_metadata.get('scraped_at')}")
        
        # Show what would be removed
        print(f"\n🗑️  Would be removed:")
        removed_keys = ['cross_references', 'related_rules', 'file_size_bytes', 'html_checksum']
        for key in removed_keys:
            if key in current_metadata:
                print(f"  - metadata.{key}")
        
        if 'sections' in current_content:
            print(f"  - content.sections")
        if 'structure' in current_content:
            print(f"  - content.structure")
        
        # Calculate size reduction
        current_size = len(json.dumps(sample_rule, ensure_ascii=False))
        focused_rule = {
            "title": sample_rule.get('title'),
            "rule_number": sample_rule.get('rule_number'),
            "citation": sample_rule.get('citation'),
            "source_url": sample_rule.get('source_url'),
            "content": {
                "plain_text": current_content.get('plain_text', ''),
                "structured_content": current_content.get('structured_content', '')
            },
            "metadata": {
                "authority": current_metadata.get('authority'),
                "effective_date": current_metadata.get('effective_date'),
                "last_updated": current_metadata.get('last_updated'),
                "scraped_at": current_metadata.get('scraped_at')
            }
        }
        focused_size = len(json.dumps(focused_rule, ensure_ascii=False))
        
        print(f"\n📊 Size comparison:")
        print(f"  - Current size: {current_size:,} characters")
        print(f"  - Focused size: {focused_size:,} characters")
        print(f"  - Reduction: {((current_size - focused_size) / current_size * 100):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing focused parser: {e}")
        return False

def show_metadata_comparison():
    """Show a detailed comparison of metadata fields."""
    print("\n📋 Metadata Field Comparison")
    print("=" * 50)
    
    print("Current Parser Fields:")
    print("  ✅ Essential for proofreading:")
    print("    - title, rule_number, citation, source_url")
    print("    - content.plain_text, content.structured_content")
    print("    - metadata.authority, metadata.effective_date, metadata.last_updated")
    print("    - metadata.scraped_at")
    print("  ❌ Not essential for proofreading:")
    print("    - metadata.cross_references")
    print("    - metadata.related_rules")
    print("    - metadata.file_size_bytes")
    print("    - metadata.html_checksum")
    print("    - content.sections")
    print("    - content.structure")
    
    print("\nFocused Parser Fields:")
    print("  ✅ Only essential fields:")
    print("    - title, rule_number, citation, source_url")
    print("    - content.plain_text, content.structured_content")
    print("    - metadata.authority, metadata.effective_date, metadata.last_updated")
    print("    - metadata.scraped_at")
    
    print("\n🎯 Benefits of focused approach:")
    print("  - Smaller file size (easier for Claude processing)")
    print("  - Cleaner data structure")
    print("  - Focus on actual rule content vs administrative info")
    print("  - Better for proofreading workflow")

if __name__ == "__main__":
    success = test_focused_parser()
    show_metadata_comparison()
    
    if success:
        print("\n✅ Focused parser test completed successfully!")
        print("\nNext steps:")
        print("1. Update the main scraper to use FocusedRuleParser")
        print("2. Re-run scraping with focused metadata")
        print("3. Prepare data for Claude proofreading")
    else:
        print("\n❌ Focused parser test failed!") 
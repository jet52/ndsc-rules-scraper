#!/usr/bin/env python3
"""
Script to examine a sample rule and see all metadata being captured.
"""

import json

def examine_sample_rule():
    """Examine a sample rule to see all metadata."""
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("📋 Sample Rule Analysis")
        print("=" * 50)
        
        # Get first rule from first category
        categories = data['data']['data']['categories']
        if not categories:
            print("❌ No categories found")
            return
        
        first_category = categories[0]
        category_name = first_category.get('category_name', 'Unknown')
        print(f"Category: {category_name}")
        
        rules = first_category.get('rules', [])
        if not rules:
            print("❌ No rules found")
            return
        
        sample_rule = rules[0]
        print(f"\n📄 Sample Rule: {sample_rule.get('title', 'Unknown')}")
        print("-" * 50)
        
        # Show all top-level keys
        print("Top-level keys:")
        for key in sample_rule.keys():
            print(f"  - {key}")
        
        # Show metadata details
        if 'metadata' in sample_rule:
            print(f"\n📋 Metadata:")
            metadata = sample_rule['metadata']
            for key, value in metadata.items():
                print(f"  - {key}: {value}")
        
        # Show content structure
        if 'content' in sample_rule:
            print(f"\n📝 Content structure:")
            content = sample_rule['content']
            for key, value in content.items():
                if key in ['plain_text', 'structured_content']:
                    print(f"  - {key}: {len(str(value))} characters")
                else:
                    print(f"  - {key}: {type(value)}")
        
        # Show a snippet of the structured content
        if 'content' in sample_rule and 'structured_content' in sample_rule['content']:
            structured = sample_rule['content']['structured_content']
            print(f"\n📝 Structured content preview (first 500 chars):")
            print("-" * 50)
            print(structured[:500] + "..." if len(structured) > 500 else structured)
        
        return True
        
    except Exception as e:
        print(f"❌ Error examining sample rule: {e}")
        return False

if __name__ == "__main__":
    examine_sample_rule() 
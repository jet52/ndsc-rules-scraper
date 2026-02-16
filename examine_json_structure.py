#!/usr/bin/env python3
"""
Examine JSON structure to understand available categories.
"""

import json

def examine_json_structure():
    """Examine the JSON file structure."""
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("JSON Structure Analysis")
        print("=" * 50)
        
        # Check top-level structure
        print(f"Top-level keys: {list(data.keys())}")
        
        # Check metadata
        if 'metadata' in data:
            print(f"\nMetadata:")
            for key, value in data['metadata'].items():
                print(f"  {key}: {value}")
        
        # Check data structure
        if 'data' in data:
            print(f"\nData keys: {list(data['data'].keys())}")
            
            # Check if there's nested data
            if 'data' in data['data']:
                print(f"Nested data keys: {list(data['data']['data'].keys())}")
                
                # Check categories
                categories = data['data']['data'].get('categories', [])
                print(f"\nCategories found: {len(categories)}")
                
                for i, category in enumerate(categories):
                    category_name = category.get('category_name', 'Unknown')
                    rule_count = len(category.get('rules', []))
                    print(f"  {i+1}. {category_name} ({rule_count} rules)")
            else:
                # Direct categories
                categories = data['data'].get('categories', [])
                print(f"\nCategories found: {len(categories)}")
                
                for i, category in enumerate(categories):
                    category_name = category.get('category_name', 'Unknown')
                    rule_count = len(category.get('rules', []))
                    print(f"  {i+1}. {category_name} ({rule_count} rules)")
        
        # Check for other possible structures
        print(f"\nAll possible paths to categories:")
        possible_paths = [
            ('data.categories', data.get('data', {}).get('categories', [])),
            ('data.data.categories', data.get('data', {}).get('data', {}).get('categories', [])),
            ('categories', data.get('categories', [])),
        ]
        
        for path, categories in possible_paths:
            print(f"  {path}: {len(categories)} categories")
            if categories:
                for cat in categories[:3]:  # Show first 3
                    print(f"    - {cat.get('category_name', 'Unknown')}")
                if len(categories) > 3:
                    print(f"    ... and {len(categories) - 3} more")
        
    except Exception as e:
        print(f"Error examining JSON: {e}")

if __name__ == "__main__":
    examine_json_structure() 
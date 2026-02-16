#!/usr/bin/env python3
"""
Simple script to examine the structure of the output JSON file.
"""

import json

def examine_structure():
    """Examine the structure of the output JSON file."""
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("📋 JSON Structure Analysis")
        print("=" * 50)
        
        print(f"Top-level keys: {list(data.keys())}")
        
        if 'metadata' in data:
            print(f"Metadata keys: {list(data['metadata'].keys())}")
        
        if 'data' in data:
            print(f"Data keys: {list(data['data'].keys())}")
            
            # Check nested structure
            if 'data' in data['data']:
                print(f"Data['data'] keys: {list(data['data']['data'].keys())}")
                
                # Check if categories is a list or dict
                categories_data = data['data']['data'].get('categories')
                if isinstance(categories_data, list):
                    print(f"Categories is a list with {len(categories_data)} items")
                    if categories_data:
                        first_category = categories_data[0]
                        print(f"First category type: {type(first_category)}")
                        if isinstance(first_category, dict):
                            print(f"First category keys: {list(first_category.keys())}")
                            if 'name' in first_category:
                                print(f"First category name: {first_category['name']}")
                            if 'rules' in first_category:
                                rules = first_category['rules']
                                print(f"Number of rules in first category: {len(rules)}")
                                if rules:
                                    first_rule = rules[0]
                                    print(f"First rule keys: {list(first_rule.keys())}")
                                    if 'content' in first_rule:
                                        content = first_rule['content']
                                        print(f"Content keys: {list(content.keys())}")
                                        if 'plain_text' in content:
                                            print(f"Plain text length: {len(content['plain_text'])} characters")
                                        if 'structured_content' in content:
                                            print(f"Structured content length: {len(content['structured_content'])} characters")
                elif isinstance(categories_data, dict):
                    print(f"Categories is a dict with keys: {list(categories_data.keys())}")
                else:
                    print(f"Categories is of type: {type(categories_data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error examining structure: {e}")
        return False

if __name__ == "__main__":
    examine_structure() 
#!/usr/bin/env python3
"""
Minimal test script for ND Court Rules Scraper.
Tests basic functionality with built-in Python modules.
"""

import sys
import os
import json
import re
import hashlib
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_builtin_modules():
    """Test that all required built-in modules are available."""
    print("Testing built-in modules...")
    
    required_modules = [
        'sys', 'os', 'json', 're', 'hashlib', 'time', 'pathlib'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False
    
    return True

def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        "config.yaml",
        "src/main.py",
        "src/scraper/nd_courts_scraper.py",
        "src/scraper/rule_parser.py",
        "src/scraper/citation_extractor.py",
        "src/utils/logger.py",
        "src/utils/file_utils.py"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            return False
    
    return True

def test_config_parsing():
    """Test config.yaml parsing without yaml module."""
    print("\nTesting config.yaml parsing...")
    
    try:
        with open("config.yaml", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic structure validation
        required_sections = ['scraping:', 'rule_categories:', 'output:']
        for section in required_sections:
            if section in content:
                print(f"✅ Found {section}")
            else:
                print(f"❌ Missing {section}")
                return False
        
        # Count rule categories
        lines = content.split('\n')
        category_count = 0
        for line in lines:
            if line.strip().startswith('- "') and '"' in line:
                category_count += 1
        
        print(f"✅ Found {category_count} rule categories")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.yaml: {e}")
        return False

def test_python_syntax():
    """Test Python syntax of key files."""
    print("\nTesting Python syntax...")
    
    python_files = [
        "src/main.py",
        "src/scraper/nd_courts_scraper.py",
        "src/scraper/rule_parser.py",
        "src/scraper/citation_extractor.py",
        "src/utils/logger.py",
        "src/utils/file_utils.py"
    ]
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, file_path, 'exec')
            print(f"✅ {file_path} - syntax OK")
        except SyntaxError as e:
            print(f"❌ {file_path} - syntax error: {e}")
            return False
        except Exception as e:
            print(f"❌ {file_path} - error: {e}")
            return False
    
    return True

def test_directory_creation():
    """Test that required directories can be created."""
    print("\nTesting directory creation...")
    
    required_dirs = [
        "data",
        "data/raw",
        "data/processed",
        "data/metadata"
    ]
    
    for dir_path in required_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"✅ {dir_path}")
        except Exception as e:
            print(f"❌ {dir_path} - error: {e}")
            return False
    
    return True

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\nTesting basic functionality...")
    
    # Test JSON handling
    try:
        test_data = {
            "test": "data",
            "number": 42,
            "list": [1, 2, 3]
        }
        json_str = json.dumps(test_data)
        parsed_data = json.loads(json_str)
        assert parsed_data == test_data
        print("✅ JSON serialization/deserialization")
    except Exception as e:
        print(f"❌ JSON test failed: {e}")
        return False
    
    # Test regex
    try:
        text = "Rule 1. Scope of Rules"
        pattern = r'Rule\s+(\d+)'
        match = re.search(pattern, text)
        assert match and match.group(1) == "1"
        print("✅ Regex pattern matching")
    except Exception as e:
        print(f"❌ Regex test failed: {e}")
        return False
    
    # Test hashlib
    try:
        test_content = "test content"
        checksum = hashlib.sha256(test_content.encode('utf-8')).hexdigest()
        assert len(checksum) == 64
        print("✅ SHA256 checksum generation")
    except Exception as e:
        print(f"❌ Hashlib test failed: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    print("🧪 Minimal ND Court Rules Scraper Test")
    print("=" * 60)
    
    tests = [
        test_builtin_modules,
        test_file_structure,
        test_config_parsing,
        test_python_syntax,
        test_directory_creation,
        test_basic_functionality
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All minimal tests passed!")
        print("\nNext steps:")
        print("1. Install external dependencies:")
        print("   python -m pip install pyyaml requests beautifulsoup4 lxml retrying tqdm")
        print("2. Run simple test: python simple_test.py")
        print("3. Run full test: python test_scraper.py")
        print("4. Run scraper: python src/main.py --verbose --categories 'Appellate Procedure' 'Administrative Rules'")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
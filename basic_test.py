#!/usr/bin/env python3
"""
Basic test script for ND Court Rules Scraper.
Tests file structure and basic functionality without external dependencies.
"""

import os
import sys
from pathlib import Path

def test_file_structure():
    """Test that all required files exist."""
    print("Testing file structure...")
    
    required_files = [
        "config.yaml",
        "src/main.py",
        "src/scraper/nd_courts_scraper.py",
        "src/scraper/rule_parser.py",
        "src/scraper/citation_extractor.py",
        "src/utils/logger.py",
        "src/utils/file_utils.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

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
    
    print("✅ All Python files have valid syntax")
    return True

def test_config_yaml():
    """Test that config.yaml can be read."""
    print("\nTesting config.yaml...")
    
    try:
        with open("config.yaml", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic YAML structure check
        if "scraping:" in content and "rule_categories:" in content:
            print("✅ config.yaml structure looks valid")
            return True
        else:
            print("❌ config.yaml missing required sections")
            return False
    except Exception as e:
        print(f"❌ Error reading config.yaml: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist or can be created."""
    print("\nTesting directory structure...")
    
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
    
    print("✅ All required directories are ready")
    return True

def main():
    """Main test function."""
    print("🧪 Basic ND Court Rules Scraper Test")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_python_syntax,
        test_config_yaml,
        test_directory_structure
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All basic tests passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run simple test: python simple_test.py")
        print("3. Run full test: python test_scraper.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
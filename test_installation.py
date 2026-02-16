#!/usr/bin/env python3
"""
Test script to verify installation and basic functionality.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        import requests
        print("✅ requests")
    except ImportError as e:
        print(f"❌ requests: {e}")
        return False
    
    try:
        import beautifulsoup4
        print("✅ beautifulsoup4")
    except ImportError as e:
        print(f"❌ beautifulsoup4: {e}")
        return False
    
    try:
        import yaml
        print("✅ pyyaml")
    except ImportError as e:
        print(f"❌ pyyaml: {e}")
        return False
    
    try:
        import anthropic
        print("✅ anthropic")
    except ImportError as e:
        print(f"❌ anthropic: {e}")
        return False
    
    try:
        import click
        print("✅ click")
    except ImportError as e:
        print(f"❌ click: {e}")
        return False
    
    try:
        import retrying
        print("✅ retrying")
    except ImportError as e:
        print(f"❌ retrying: {e}")
        return False
    
    try:
        import tqdm
        print("✅ tqdm")
    except ImportError as e:
        print(f"❌ tqdm: {e}")
        return False
    
    return True

def test_scraper_imports():
    """Test that scraper modules can be imported."""
    print("\n🔍 Testing scraper imports...")
    
    # Add src to path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    try:
        from utils.logger import ScraperLogger, get_logger
        print("✅ utils.logger")
    except ImportError as e:
        print(f"❌ utils.logger: {e}")
        return False
    
    try:
        from utils.file_utils import FileManager
        print("✅ utils.file_utils")
    except ImportError as e:
        print(f"❌ utils.file_utils: {e}")
        return False
    
    try:
        from scraper.rule_parser import RuleParser
        print("✅ scraper.rule_parser")
    except ImportError as e:
        print(f"❌ scraper.rule_parser: {e}")
        return False
    
    try:
        from scraper.citation_extractor import CitationExtractor
        print("✅ scraper.citation_extractor")
    except ImportError as e:
        print(f"❌ scraper.citation_extractor: {e}")
        return False
    
    try:
        from scraper.nd_courts_scraper import NDCourtsScraper
        print("✅ scraper.nd_courts_scraper")
    except ImportError as e:
        print(f"❌ scraper.nd_courts_scraper: {e}")
        return False
    
    return True

def test_config_file():
    """Test that configuration file exists and is valid."""
    print("\n🔍 Testing configuration file...")
    
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("❌ config.yaml not found")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print("✅ config.yaml is valid YAML")
        
        # Check for required sections
        required_sections = ['scraping', 'output', 'logging']
        for section in required_sections:
            if section in config:
                print(f"✅ {section} section found")
            else:
                print(f"⚠️  {section} section missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.yaml: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist."""
    print("\n🔍 Testing directory structure...")
    
    required_dirs = [
        "src",
        "src/scraper", 
        "src/utils"
    ]
    
    for directory in required_dirs:
        if Path(directory).exists():
            print(f"✅ {directory}")
        else:
            print(f"❌ {directory} missing")
            return False
    
    return True

def test_basic_functionality():
    """Test basic scraper functionality."""
    print("\n🔍 Testing basic functionality...")
    
    try:
        # Add src to path
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        from utils.logger import get_logger
        from scraper.nd_courts_scraper import NDCourtsScraper
        
        # Test logger creation
        logger = get_logger("config.yaml", verbose=False)
        print("✅ Logger created successfully")
        
        # Test scraper initialization
        scraper = NDCourtsScraper("config.yaml", verbose=False)
        print("✅ Scraper initialized successfully")
        
        # Test statistics
        stats = scraper.get_scraping_statistics()
        print("✅ Statistics retrieval works")
        
        # Cleanup
        scraper.cleanup()
        print("✅ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 North Dakota Court Rules Scraper - Installation Test")
    print("=" * 60)
    
    tests = [
        ("Dependencies", test_imports),
        ("Scraper Modules", test_scraper_imports),
        ("Configuration", test_config_file),
        ("Directory Structure", test_directory_structure),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The scraper is ready to use.")
        print("\nTo run the scraper:")
        print("  python src/main.py")
        print("\nFor verbose output:")
        print("  python src/main.py --verbose")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        print("\nTo install missing dependencies:")
        print("  pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
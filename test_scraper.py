#!/usr/bin/env python3
"""
Test script for ND Court Rules Scraper validation.
Runs a test scrape and validates the output format and quality.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.nd_courts_scraper import NDCourtsScraper
from utils.logger import get_logger
from utils.file_utils import FileManager


class ScraperValidator:
    """Validates scraper output and functionality."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the validator."""
        self.config_path = config_path
        self.logger = get_logger(config_path, verbose=True)
        self.file_manager = FileManager(config_path, self.logger)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def create_test_config(self) -> str:
        """Create a test configuration for validation."""
        test_config = self.config.copy()
        
        # Limit to test categories
        test_config['rule_categories'] = [
            "Appellate Procedure",
            "Administrative Rules"
        ]
        
        # Enable verbose logging
        test_config['logging']['level'] = "DEBUG"
        test_config['logging']['verbose'] = True
        
        # Slightly slower for testing
        test_config['scraping']['request_delay'] = 0.5
        
        # Save test config
        test_config_path = "test_config.yaml"
        with open(test_config_path, 'w') as f:
            yaml.dump(test_config, f, default_flow_style=False, indent=2)
        
        self.logger.info(f"Created test configuration: {test_config_path}")
        return test_config_path

    def run_test_scrape(self, test_config_path: str) -> Dict[str, Any]:
        """Run the test scrape."""
        self.logger.info("Starting test scrape...")
        
        # Initialize scraper with test config
        scraper = NDCourtsScraper(test_config_path, verbose=True)
        
        try:
            # Run the scrape
            start_time = time.time()
            results = scraper.scrape_all_rules()
            end_time = time.time()
            
            results['scraping_time'] = end_time - start_time
            results['test_config_path'] = test_config_path
            
            self.logger.info(f"Test scrape completed in {results['scraping_time']:.2f} seconds")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Test scrape failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "scraping_time": 0
            }
        finally:
            scraper.cleanup()

    def validate_output_structure(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the output structure and format."""
        validation_results = {
            "structure_valid": False,
            "schema_compliance": False,
            "content_quality": False,
            "metadata_completeness": False,
            "checksums_valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check if scrape was successful
            if not results.get('success', False):
                validation_results["errors"].append("Scrape was not successful")
                return validation_results
            
            # Check if output file exists
            output_file = "data/processed/nd_court_rules_complete.json"
            if not Path(output_file).exists():
                validation_results["errors"].append(f"Output file not found: {output_file}")
                return validation_results
            
            # Load and validate the output file
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate top-level structure
            if not self._validate_top_level_structure(data):
                validation_results["errors"].append("Invalid top-level structure")
                return validation_results
            
            validation_results["structure_valid"] = True
            
            # Validate schema compliance
            if self._validate_schema_compliance(data):
                validation_results["schema_compliance"] = True
            else:
                validation_results["errors"].append("Schema compliance validation failed")
            
            # Validate content quality
            content_quality = self._validate_content_quality(data)
            validation_results["content_quality"] = content_quality["valid"]
            validation_results["warnings"].extend(content_quality["warnings"])
            
            # Validate metadata completeness
            metadata_quality = self._validate_metadata_completeness(data)
            validation_results["metadata_completeness"] = metadata_quality["valid"]
            validation_results["warnings"].extend(metadata_quality["warnings"])
            
            # Validate checksums
            if self._validate_checksums(data):
                validation_results["checksums_valid"] = True
            else:
                validation_results["warnings"].append("Some checksums could not be validated")
            
            return validation_results
            
        except Exception as e:
            validation_results["errors"].append(f"Validation error: {e}")
            return validation_results

    def _validate_top_level_structure(self, data: Dict[str, Any]) -> bool:
        """Validate the top-level structure of the output."""
        required_top_level = ["metadata", "data"]
        required_metadata = ["generated_at", "source", "version", "schema_version", "total_rules", "total_categories"]
        required_data = ["categories"]
        
        # Check top-level keys
        if not all(key in data for key in required_top_level):
            return False
        
        # Check metadata keys
        if not all(key in data["metadata"] for key in required_metadata):
            return False
        
        # Check data keys
        if not all(key in data["data"] for key in required_data):
            return False
        
        return True

    def _validate_schema_compliance(self, data: Dict[str, Any]) -> bool:
        """Validate schema compliance."""
        try:
            categories = data["data"]["categories"]
            
            for category in categories:
                # Check category structure
                if not all(key in category for key in ["category_name", "category_url", "rule_count", "rules"]):
                    return False
                
                # Check rules structure
                for rule in category["rules"]:
                    required_rule_keys = ["title", "rule_number", "citation", "source_url", "content", "metadata"]
                    if not all(key in rule for key in required_rule_keys):
                        return False
                    
                    # Check content structure
                    content = rule["content"]
                    required_content_keys = ["plain_text", "structured_content", "sections", "structure"]
                    if not all(key in content for key in required_content_keys):
                        return False
                    
                    # Check metadata structure
                    metadata = rule["metadata"]
                    required_metadata_keys = ["scraped_at", "file_size_bytes", "html_checksum"]
                    if not all(key in metadata for key in required_metadata_keys):
                        return False
            
            return True
            
        except Exception:
            return False

    def _validate_content_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content quality."""
        result = {"valid": True, "warnings": []}
        
        try:
            categories = data["data"]["categories"]
            
            for category in categories:
                for rule in category["rules"]:
                    content = rule["content"]
                    
                    # Check if plain text is not empty
                    if not content["plain_text"].strip():
                        result["warnings"].append(f"Empty plain text for rule: {rule['title']}")
                    
                    # Check if structured content is not empty
                    if not content["structured_content"].strip():
                        result["warnings"].append(f"Empty structured content for rule: {rule['title']}")
                    
                    # Check if markdown has proper formatting
                    if not content["structured_content"].startswith("#"):
                        result["warnings"].append(f"Structured content doesn't start with heading for rule: {rule['title']}")
                    
                    # Check section depth limiting
                    max_depth = self._check_section_depth(content["sections"])
                    if max_depth > 4:
                        result["warnings"].append(f"Section depth exceeds 4 levels for rule: {rule['title']} (max: {max_depth})")
            
            return result
            
        except Exception as e:
            result["valid"] = False
            result["warnings"].append(f"Content quality validation error: {e}")
            return result

    def _check_section_depth(self, sections: List[Dict[str, Any]], current_depth: int = 0) -> int:
        """Check the maximum depth of sections."""
        max_depth = current_depth
        
        for section in sections:
            level = section.get("level", 0)
            max_depth = max(max_depth, level)
            
            # Check subsections
            subsections = section.get("subsections", [])
            if subsections:
                subsection_depth = self._check_section_depth(subsections, level)
                max_depth = max(max_depth, subsection_depth)
        
        return max_depth

    def _validate_metadata_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata completeness."""
        result = {"valid": True, "warnings": []}
        
        try:
            categories = data["data"]["categories"]
            
            for category in categories:
                for rule in category["rules"]:
                    metadata = rule["metadata"]
                    
                    # Check if required metadata fields are present
                    if not metadata.get("scraped_at"):
                        result["warnings"].append(f"Missing scraped_at for rule: {rule['title']}")
                    
                    if not metadata.get("file_size_bytes"):
                        result["warnings"].append(f"Missing file_size_bytes for rule: {rule['title']}")
                    
                    if not metadata.get("html_checksum"):
                        result["warnings"].append(f"Missing html_checksum for rule: {rule['title']}")
                    
                    # Check if file size is reasonable
                    file_size = metadata.get("file_size_bytes", 0)
                    if file_size < 100:
                        result["warnings"].append(f"Very small file size for rule: {rule['title']} ({file_size} bytes)")
                    elif file_size > 100000:
                        result["warnings"].append(f"Very large file size for rule: {rule['title']} ({file_size} bytes)")
            
            return result
            
        except Exception as e:
            result["valid"] = False
            result["warnings"].append(f"Metadata validation error: {e}")
            return result

    def _validate_checksums(self, data: Dict[str, Any]) -> bool:
        """Validate checksums."""
        try:
            categories = data["data"]["categories"]
            
            for category in categories:
                for rule in category["rules"]:
                    metadata = rule["metadata"]
                    checksum = metadata.get("html_checksum")
                    
                    if checksum:
                        # Basic checksum format validation
                        if not checksum.startswith("sha256:"):
                            return False
                        
                        # Check if it's a valid hex string
                        hex_part = checksum[7:]  # Remove "sha256:" prefix
                        if len(hex_part) != 64:  # SHA256 is 64 hex characters
                            return False
                        
                        try:
                            int(hex_part, 16)  # Validate hex format
                        except ValueError:
                            return False
            
            return True
            
        except Exception:
            return False

    def generate_validation_report(self, results: Dict[str, Any], validation: Dict[str, Any]) -> str:
        """Generate a comprehensive validation report."""
        report = []
        report.append("=" * 80)
        report.append("ND COURT RULES SCRAPER - VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Scraping Results
        report.append("SCRAPING RESULTS:")
        report.append("-" * 40)
        if results.get('success', False):
            stats = results.get('statistics', {})
            report.append(f"✅ Scraping completed successfully")
            report.append(f"   Categories processed: {stats.get('categories_processed', 0)}")
            report.append(f"   Total rules scraped: {stats.get('total_rules_scraped', 0)}")
            report.append(f"   Successful rules: {stats.get('successful_rules', 0)}")
            report.append(f"   Failed rules: {stats.get('failed_rules', 0)}")
            report.append(f"   Scraping time: {results.get('scraping_time', 0):.2f} seconds")
        else:
            report.append(f"❌ Scraping failed: {results.get('error', 'Unknown error')}")
        report.append("")
        
        # Validation Results
        report.append("VALIDATION RESULTS:")
        report.append("-" * 40)
        
        validation_checks = [
            ("Structure Valid", "structure_valid"),
            ("Schema Compliance", "schema_compliance"),
            ("Content Quality", "content_quality"),
            ("Metadata Completeness", "metadata_completeness"),
            ("Checksums Valid", "checksums_valid")
        ]
        
        for check_name, check_key in validation_checks:
            status = "✅ PASS" if validation.get(check_key, False) else "❌ FAIL"
            report.append(f"{status} {check_name}")
        
        report.append("")
        
        # Errors
        if validation.get("errors"):
            report.append("ERRORS:")
            report.append("-" * 40)
            for error in validation["errors"]:
                report.append(f"❌ {error}")
            report.append("")
        
        # Warnings
        if validation.get("warnings"):
            report.append("WARNINGS:")
            report.append("-" * 40)
            for warning in validation["warnings"]:
                report.append(f"⚠️  {warning}")
            report.append("")
        
        # File Information
        output_file = "data/processed/nd_court_rules_complete.json"
        if Path(output_file).exists():
            file_size = Path(output_file).stat().st_size
            report.append("OUTPUT FILE:")
            report.append("-" * 40)
            report.append(f"File: {output_file}")
            report.append(f"Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            report.append("")
        
        # Overall Status
        all_passed = all(validation.get(key, False) for key in ["structure_valid", "schema_compliance", "content_quality", "metadata_completeness"])
        overall_status = "✅ ALL VALIDATIONS PASSED" if all_passed else "❌ SOME VALIDATIONS FAILED"
        report.append("OVERALL STATUS:")
        report.append("-" * 40)
        report.append(overall_status)
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

    def run_full_validation(self) -> Dict[str, Any]:
        """Run the complete validation process."""
        self.logger.info("Starting full validation process...")
        
        # Create test configuration
        test_config_path = self.create_test_config()
        
        # Run test scrape
        results = self.run_test_scrape(test_config_path)
        
        # Validate output
        validation = self.validate_output_structure(results)
        
        # Generate report
        report = self.generate_validation_report(results, validation)
        
        # Save report
        report_path = "validation_report.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Print report
        print(report)
        
        # Clean up test config
        if Path(test_config_path).exists():
            Path(test_config_path).unlink()
        
        return {
            "results": results,
            "validation": validation,
            "report": report,
            "report_path": report_path
        }


def main():
    """Main test function."""
    print("🧪 ND Court Rules Scraper - Validation Test")
    print("=" * 60)
    
    # Check if required files exist
    required_files = ["config.yaml", "src/main.py"]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Required file missing: {file_path}")
            sys.exit(1)
    
    # Initialize validator
    validator = ScraperValidator()
    
    try:
        # Run full validation
        validation_results = validator.run_full_validation()
        
        # Check overall success
        validation = validation_results["validation"]
        all_passed = all(validation.get(key, False) for key in ["structure_valid", "schema_compliance", "content_quality", "metadata_completeness"])
        
        if all_passed:
            print("\n🎉 Validation completed successfully!")
            print(f"📄 Detailed report saved to: {validation_results['report_path']}")
            sys.exit(0)
        else:
            print("\n⚠️  Validation completed with issues.")
            print(f"📄 Detailed report saved to: {validation_results['report_path']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
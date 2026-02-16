#!/usr/bin/env python3
"""
Enhanced main entry point for the ND Court Rules Scraper.
Provides comprehensive command-line interface with individual rule set scraping.
"""

import os
import sys
import argparse
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scraper.nd_courts_scraper import NDCourtsScraper
from utils.logger import get_logger
from utils.file_utils import FileManager


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up comprehensive command line argument parser."""
    parser = argparse.ArgumentParser(
        description="North Dakota Court Rules Scraper - Enhanced Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Scrape all rule sets (default)
  python src/main_enhanced.py

  # Scrape only specific rule sets
  python src/main_enhanced.py --rule-sets "Appellate Procedure" "Civil Procedure"

  # Update existing data with new scraping (preserves other rule sets)
  python src/main_enhanced.py --update-existing --rule-sets "Evidence"

  # Verbose logging with custom config
  python src/main_enhanced.py --verbose --config custom.yaml

  # Dry run to test without saving
  python src/main_enhanced.py --dry-run --rule-sets "Administrative Rules"

  # Show available rule sets
  python src/main_enhanced.py --list-rule-sets

  # Validate existing data
  python src/main_enhanced.py --validate-only

  # Generate markdown files
  python src/main_enhanced.py --generate-markdown

AVAILABLE RULE SETS:
  • Appellate Procedure
  • Civil Procedure  
  • Criminal Procedure
  • Juvenile Procedure
  • Evidence
  • Rules of Court
  • Administrative Rules
  • Administrative Orders
  • Admission to Practice Rules
  • Continuing Legal Education
  • Professional Conduct
  • Lawyer Discipline
  • Standards for Imposing Lawyer Sanctions
  • Code of Judicial Conduct
  • Judicial Conduct Commission
  • Rules on Procedural Rules, Administrative Rules and Administrative Orders
  • Rules on Local Court Procedural Rules and Administrative Rules
  • Limited Practice of Law by Law Students
  • Local Court Procedural and Administrative Rules
        """
    )
    
    # Basic options
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging and debugging output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test scraping without saving files (for debugging)'
    )
    
    # Rule set selection
    parser.add_argument(
        '--rule-sets', '-r',
        nargs='+',
        help='Specific rule sets to scrape (default: all available)'
    )
    
    parser.add_argument(
        '--list-rule-sets',
        action='store_true',
        help='List all available rule sets and exit'
    )
    
    parser.add_argument(
        '--update-existing',
        action='store_true',
        help='Update existing data with new scraping (preserves other rule sets)'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir', '-o',
        help='Override output directory from config'
    )
    
    parser.add_argument(
        '--output-file',
        help='Override output filename (default: nd_court_rules_complete.json)'
    )
    
    # Scraping options
    parser.add_argument(
        '--delay',
        type=float,
        help='Override request delay in seconds'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        help='Override maximum retry attempts'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        help='Override request timeout in seconds'
    )
    
    # Data management
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up old files before scraping'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate existing data without scraping'
    )
    
    parser.add_argument(
        '--generate-markdown',
        action='store_true',
        help='Generate markdown files for all rule sets'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of existing data before updating'
    )
    
    # Information options
    parser.add_argument(
        '--version',
        action='version',
        version='ND Court Rules Scraper Enhanced v1.1'
    )
    
    return parser


def get_available_rule_sets() -> List[str]:
    """Get list of all available rule sets."""
    return [
        "Appellate Procedure",
        "Civil Procedure",
        "Criminal Procedure", 
        "Juvenile Procedure",
        "Evidence",
        "Rules of Court",
        "Administrative Rules",
        "Administrative Orders",
        "Admission to Practice Rules",
        "Continuing Legal Education",
        "Professional Conduct",
        "Lawyer Discipline",
        "Standards for Imposing Lawyer Sanctions",
        "Code of Judicial Conduct",
        "Judicial Conduct Commission",
        "Rules on Procedural Rules, Administrative Rules and Administrative Orders",
        "Rules on Local Court Procedural Rules and Administrative Rules",
        "Limited Practice of Law by Law Students",
        "Local Court Procedural and Administrative Rules"
    ]


def list_rule_sets():
    """List all available rule sets."""
    print("Available Rule Sets:")
    print("=" * 50)
    
    rule_sets = get_available_rule_sets()
    for i, rule_set in enumerate(rule_sets, 1):
        print(f"{i:2d}. {rule_set}")
    
    print(f"\nTotal: {len(rule_sets)} rule sets available")
    print("\nUsage examples:")
    print("  python src/main_enhanced.py --rule-sets 'Appellate Procedure' 'Civil Procedure'")
    print("  python src/main_enhanced.py --rule-sets Evidence")
    print("  python src/main_enhanced.py --update-existing --rule-sets 'Administrative Rules'")


def validate_rule_sets(rule_sets: List[str]) -> bool:
    """Validate that specified rule sets are available."""
    available = get_available_rule_sets()
    invalid = [rs for rs in rule_sets if rs not in available]
    
    if invalid:
        print(f"Error: Invalid rule sets specified: {invalid}")
        print("\nAvailable rule sets:")
        for rs in available:
            print(f"  • {rs}")
        return False
    
    return True


def load_existing_data(output_file: str) -> Optional[Dict[str, Any]]:
    """Load existing data if available."""
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse existing data: {e}")
        return None


def backup_existing_data(output_file: str, logger):
    """Create backup of existing data."""
    if not Path(output_file).exists():
        return
    
    backup_file = output_file.replace('.json', f'_backup_{int(time.time())}.json')
    try:
        import shutil
        shutil.copy2(output_file, backup_file)
        logger.info(f"Created backup: {backup_file}")
        print(f"Backup created: {backup_file}")
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        print(f"Warning: Could not create backup: {e}")


def merge_rule_data(existing_data: Dict[str, Any], new_data: Dict[str, Any], 
                   target_rule_sets: List[str], logger) -> Dict[str, Any]:
    """Merge new rule data with existing data, updating only specified rule sets."""
    if not existing_data:
        return new_data
    
    # Create a copy of existing data
    merged_data = existing_data.copy()
    
    # Get existing categories
    existing_categories = merged_data.get('data', {}).get('data', {}).get('categories', [])
    new_categories = new_data.get('data', {}).get('data', {}).get('categories', [])
    
    # Create a map of existing categories by name
    existing_cat_map = {cat.get('category_name'): cat for cat in existing_categories}
    
    # Update or add new categories
    for new_cat in new_categories:
        cat_name = new_cat.get('category_name')
        if cat_name in target_rule_sets:
            existing_cat_map[cat_name] = new_cat
            logger.info(f"Updated rule set: {cat_name}")
    
    # Update the merged data
    merged_data['data']['data']['categories'] = list(existing_cat_map.values())
    
    # Update metadata
    merged_data['metadata']['last_updated'] = time.time()
    merged_data['metadata']['updated_rule_sets'] = target_rule_sets
    
    return merged_data


def save_merged_data(data: Dict[str, Any], output_file: str, logger):
    """Save merged data to file."""
    try:
        # Ensure directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved merged data to: {output_file}")
        print(f"Data saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to save merged data: {e}")
        raise


def validate_existing_data(output_file: str) -> bool:
    """Validate existing data structure and content."""
    print("Validating existing data...")
    
    try:
        # Import the enhanced validator
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from validation_enhanced import RuleValidator
        
        validator = RuleValidator(output_file)
        results = validator.run_validation()
        
        if results['overall']['passed']:
            print("✅ Data validation passed")
            return True
        else:
            print("❌ Data validation failed")
            
            # Show summary of issues
            if results['failed_rules']:
                print(f"\nFailed rules: {len(results['failed_rules'])}")
                for rule in results['failed_rules'][:3]:  # Show first 3
                    print(f"  • {rule['title']} (Rule {rule['rule_number']})")
                if len(results['failed_rules']) > 3:
                    print(f"  ... and {len(results['failed_rules']) - 3} more")
            
            return False
        
    except ImportError:
        # Fallback to basic validation if enhanced validator not available
        print("Enhanced validator not available, using basic validation...")
        data = load_existing_data(output_file)
        if not data:
            print("No existing data found to validate")
            return False
        
        # Basic structure validation
        if 'metadata' not in data or 'data' not in data:
            print("Error: Invalid data structure")
            return False
        
        categories = data.get('data', {}).get('data', {}).get('categories', [])
        print(f"Found {len(categories)} rule sets in existing data")
        
        total_rules = 0
        for cat in categories:
            rule_count = len(cat.get('rules', []))
            total_rules += rule_count
            print(f"  • {cat.get('category_name')}: {rule_count} rules")
        
        print(f"\nTotal rules: {total_rules}")
        print("Basic data validation passed")
        return True
        
    except Exception as e:
        print(f"Error validating data: {e}")
        return False


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║           North Dakota Court Rules Scraper - Enhanced       ║
║                        Version 1.1                          ║
║                                                              ║
║  Scrapes and processes North Dakota court rules from        ║
║  https://www.ndcourts.gov/legal-resources/rules             ║
║                                                              ║
║  Features: Individual rule set scraping, data preservation, ║
║            incremental updates, comprehensive validation     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_summary(stats: Dict[str, Any], success: bool, mode: str = "scraping"):
    """Print operation summary."""
    print("\n" + "="*60)
    print(f"📊 {mode.upper()} SUMMARY")
    print("="*60)
    
    if success:
        print(f"✅ Operation completed successfully!")
        print(f"📁 Categories processed: {stats.get('categories_processed', 0)}")
        print(f"📄 Total rules processed: {stats.get('total_rules_scraped', 0)}")
        print(f"✅ Successful rules: {stats.get('successful_rules', 0)}")
        print(f"❌ Failed rules: {stats.get('failed_rules', 0)}")
        
        if stats.get('start_time') and stats.get('end_time'):
            duration = stats['end_time'] - stats['start_time']
            print(f"⏱️  Total time: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
        if stats.get('total_rules_scraped', 0) > 0:
            success_rate = (stats.get('successful_rules', 0) / stats.get('total_rules_scraped', 1)) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
        
    else:
        print("❌ Operation failed!")
        print(f"📄 Rules attempted: {stats.get('total_rules_scraped', 0)}")
        print(f"✅ Successful rules: {stats.get('successful_rules', 0)}")
        print(f"❌ Failed rules: {stats.get('failed_rules', 0)}")
    
    print("="*60)


def main():
    """Main entry point."""
    print_banner()
    
    # Parse command line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Handle special commands
    if args.list_rule_sets:
        list_rule_sets()
        return
    
    # Validate rule sets if specified
    if args.rule_sets and not validate_rule_sets(args.rule_sets):
        sys.exit(1)
    
    # Determine output file
    output_file = args.output_file or 'data/processed/nd_court_rules_complete.json'
    
    # Handle validation-only mode
    if args.validate_only:
        if validate_existing_data(output_file):
            print("✅ Data validation completed successfully")
        else:
            print("❌ Data validation failed")
            sys.exit(1)
        return
    
    # Handle markdown generation mode
    if args.generate_markdown:
        print("📝 Generating markdown files...")
        try:
            from utils.markdown_generator import MarkdownGenerator
            generator = MarkdownGenerator()
            generated_files = generator.generate_all_markdown(output_file)
            generator.generate_index_file(output_file)
            
            if generated_files:
                print(f"✅ Successfully generated {len(generated_files)} markdown files!")
                print(f"📁 Files saved to: data/markdown/")
                print("📄 Index file: data/markdown/README.md")
            else:
                print("❌ No markdown files were generated")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error generating markdown files: {e}")
            sys.exit(1)
        return
    
    # Load configuration
    print(f"📋 Loading configuration from: {args.config}")
    try:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)
    
    # Update config with command line arguments
    if args.rule_sets:
        config['rule_categories'] = args.rule_sets
    
    if args.delay is not None:
        config['scraping']['request_delay'] = args.delay
    
    if args.max_retries is not None:
        config['scraping']['max_retries'] = args.max_retries
    
    if args.timeout is not None:
        config['scraping']['timeout'] = args.timeout
    
    if args.verbose:
        config['logging']['verbose'] = True
        config['logging']['level'] = 'DEBUG'
    
    # Initialize logger
    logger = get_logger(args.config, args.verbose)
    logger.info("Starting ND Court Rules Scraper - Enhanced")
    
    # Load existing data if updating
    existing_data = None
    if args.update_existing:
        existing_data = load_existing_data(output_file)
        if existing_data:
            print(f"📁 Found existing data with {len(existing_data.get('data', {}).get('data', {}).get('categories', []))} rule sets")
        else:
            print("📁 No existing data found, will create new file")
    
    # Create backup if requested
    if args.backup and existing_data:
        backup_existing_data(output_file, logger)
    
    # Initialize scraper
    print("🚀 Initializing scraper...")
    scraper = NDCourtsScraper(args.config, args.verbose)
    
    try:
        # Start scraping
        print("🌐 Starting scraping process...")
        start_time = time.time()
        
        results = scraper.scrape_all_rules()
        
        end_time = time.time()
        duration = end_time - start_time
        results['statistics']['duration'] = duration
        
        # Handle data merging if updating existing
        if args.update_existing and existing_data and results['success']:
            print("🔄 Merging with existing data...")
            merged_data = merge_rule_data(existing_data, results['rules'], args.rule_sets or [], logger)
            save_merged_data(merged_data, output_file, logger)
        elif results['success'] and not args.dry_run:
            # Save new data
            save_merged_data(results['rules'], output_file, logger)
        
        # Print summary
        print_summary(results['statistics'], results['success'])
        
        if results['success']:
            print(f"\n📁 Output saved to: {output_file}")
            
            if args.dry_run:
                print("🔍 Dry run completed - no files were saved")
            elif args.update_existing:
                print("🔄 Data updated successfully - existing rule sets preserved")
            else:
                print("✅ New data created successfully")
        
        else:
            print(f"\n❌ Scraping failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        logger.warning("Operation interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        # Cleanup
        scraper.cleanup()
        logger.info("Scraper completed")
    
    print("\n🎉 Operation completed successfully!")


if __name__ == "__main__":
    main() 
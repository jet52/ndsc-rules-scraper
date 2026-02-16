"""
Main entry point for the ND Court Rules Scraper.
Provides command-line interface and orchestrates the scraping process.
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scraper.nd_courts_scraper import NDCourtsScraper
from utils.logger import get_logger
from utils.file_utils import FileManager


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="North Dakota Court Rules Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py                    # Run with default settings
  python src/main.py --verbose          # Enable verbose logging
  python src/main.py --config custom.yaml  # Use custom config file
  python src/main.py --dry-run          # Test without saving files
        """
    )
    
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
    
    parser.add_argument(
        '--output-dir', '-o',
        help='Override output directory from config'
    )
    
    parser.add_argument(
        '--categories',
        nargs='+',
        help='Specific rule categories to scrape (default: all)'
    )
    
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
        '--cleanup',
        action='store_true',
        help='Clean up old files before scraping'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='ND Court Rules Scraper v1.0'
    )
    
    return parser


def validate_environment() -> bool:
    """Validate that the environment is properly set up."""
    print("🔍 Validating environment...")
    
    # Check if required directories exist
    required_dirs = ['src', 'src/scraper', 'src/utils']
    for directory in required_dirs:
        if not Path(directory).exists():
            print(f"❌ Required directory missing: {directory}")
            return False
    
    # Check if required files exist
    required_files = ['config.yaml', 'requirements.txt']
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Required file missing: {file}")
            return False
    
    # Check if we can import required modules
    try:
        import requests
        from bs4 import BeautifulSoup
        import yaml
        import anthropic
        print("✅ All required packages are available")
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    print("✅ Environment validation passed")
    return True


def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration."""
    import yaml
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate required configuration sections
        required_sections = ['scraping', 'output', 'logging']
        for section in required_sections:
            if section not in config:
                print(f"⚠️  Warning: Missing configuration section: {section}")
        
        return config
        
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing configuration file: {e}")
        sys.exit(1)


def update_config_from_args(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """Update configuration with command line arguments."""
    if args.output_dir:
        config['output']['data_dir'] = args.output_dir
    
    if args.delay:
        config['scraping']['request_delay'] = args.delay
    
    if args.max_retries:
        config['scraping']['max_retries'] = args.max_retries
    
    if args.verbose:
        config['logging']['verbose'] = True
        config['logging']['level'] = 'DEBUG'
    
    if args.categories:
        config['rule_categories'] = args.categories
    
    return config


def save_updated_config(config: Dict[str, Any], config_path: str):
    """Save updated configuration back to file."""
    import yaml
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Updated configuration saved to: {config_path}")
    except Exception as e:
        print(f"⚠️  Warning: Could not save updated configuration: {e}")


def cleanup_old_files(file_manager: FileManager, logger):
    """Clean up old files if requested."""
    print("🧹 Cleaning up old files...")
    
    try:
        removed_count = file_manager.cleanup_old_files("raw", days_old=7)
        print(f"✅ Removed {removed_count} old raw files")
        
        removed_count = file_manager.cleanup_old_files("metadata", days_old=30)
        print(f"✅ Removed {removed_count} old metadata files")
        
    except Exception as e:
        print(f"⚠️  Warning: Error during cleanup: {e}")


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                North Dakota Court Rules Scraper              ║
║                        Version 1.0                          ║
║                                                              ║
║  Scrapes and processes North Dakota court rules from        ║
║  https://www.ndcourts.gov/legal-resources/rules             ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_summary(stats: Dict[str, Any], success: bool):
    """Print scraping summary."""
    print("\n" + "="*60)
    print("📊 SCRAPING SUMMARY")
    print("="*60)
    
    if success:
        print(f"✅ Scraping completed successfully!")
        print(f"📁 Categories processed: {stats.get('categories_processed', 0)}")
        print(f"📄 Total rules scraped: {stats.get('total_rules_scraped', 0)}")
        print(f"✅ Successful rules: {stats.get('successful_rules', 0)}")
        print(f"❌ Failed rules: {stats.get('failed_rules', 0)}")
        
        if stats.get('start_time') and stats.get('end_time'):
            duration = stats['end_time'] - stats['start_time']
            print(f"⏱️  Total time: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
        success_rate = (stats.get('successful_rules', 0) / max(stats.get('total_rules_scraped', 1), 1)) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")
        
    else:
        print("❌ Scraping failed!")
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
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Load configuration
    print(f"📋 Loading configuration from: {args.config}")
    config = load_config(args.config)
    
    # Update configuration with command line arguments
    config = update_config_from_args(config, args)
    
    # Save updated configuration if modified
    if any([args.output_dir, args.delay, args.max_retries, args.verbose, args.categories]):
        save_updated_config(config, args.config)
    
    # Initialize logger
    logger = get_logger(args.config, args.verbose)
    logger.info("Starting ND Court Rules Scraper")
    
    # Initialize file manager
    file_manager = FileManager(args.config, logger)
    
    # Cleanup old files if requested
    if args.cleanup:
        cleanup_old_files(file_manager, logger)
    
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
        
        # Print summary
        print_summary(results['statistics'], results['success'])
        
        if results['success']:
            print("\n📁 Output files saved to:")
            print(f"   • Processed rules: {config['output']['processed_dir']}")
            print(f"   • Raw HTML: {config['output']['raw_dir']}")
            print(f"   • Metadata: {config['output']['metadata_dir']}")
            
            # List generated files
            processed_files = file_manager.get_file_list("processed")
            if processed_files:
                print(f"\n📄 Generated rule files ({len(processed_files)}):")
                for filename in processed_files:
                    file_size = file_manager.get_file_size(filename, "processed")
                    size_str = f" ({file_size:,} bytes)" if file_size else ""
                    print(f"   • {filename}.json{size_str}")
        
        else:
            print(f"\n❌ Scraping failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        logger.warning("Scraping interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        # Cleanup
        scraper.cleanup()
        logger.info("Scraper completed")
    
    print("\n🎉 Scraping process completed!")


if __name__ == "__main__":
    main() 
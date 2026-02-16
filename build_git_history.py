#!/usr/bin/env python3
"""
Build a git repository with full version history for ND Court Rules.

Usage:
    python build_git_history.py --category ndrappp
    python build_git_history.py --category ndrct --verbose
    python build_git_history.py --all --verbose
    python build_git_history.py --category ndrappp --config config.yaml
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.logger import get_logger
from orchestrator.version_history_orchestrator import VersionHistoryOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Build git repository with ND Court Rules version history"
    )
    parser.add_argument(
        '--category', '-k',
        default='ndrappp',
        help='Rule category to process (default: ndrappp)',
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Build all enabled categories',
    )
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging',
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force rebuild even if repository exists',
    )

    args = parser.parse_args()

    logger = get_logger(args.config, args.verbose)

    orchestrator = VersionHistoryOrchestrator(
        config_path=args.config,
        logger=logger,
    )

    # Determine which categories to process
    if args.all:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        categories = [
            k for k, v in config.get('git', {}).get('categories', {}).items()
            if v.get('enabled', False)
        ]
        print(f"Building git history for all enabled categories: {', '.join(categories)}")
    else:
        categories = [args.category]
        print(f"Building git history for category: {args.category}")

    print(f"Config: {args.config}")
    print()

    try:
        for category in categories:
            print(f"--- Processing: {category} ---")
            stats = orchestrator.build_git_repository(
                category=category,
                force=args.force,
            )

            print()
            print("=" * 60)
            print(f"BUILD COMPLETE: {category}")
            print("=" * 60)
            print(f"Category:           {stats['category']}")
            print(f"Rules found:        {stats['rules_found']}")
            print(f"Rules processed:    {stats['rules_processed']}")
            print(f"Versions committed: {stats['versions_committed']}")
            print(f"Duration:           {stats.get('duration_seconds', 0):.1f}s")

            if stats['errors']:
                print(f"Errors:             {len(stats['errors'])}")
                for err in stats['errors']:
                    print(f"  - {err}")

            print("=" * 60)
            print()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        orchestrator.cleanup()


if __name__ == '__main__':
    main()

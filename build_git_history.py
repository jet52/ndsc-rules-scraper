#!/usr/bin/env python3
"""
Build a git repository with full version history for ND Court Rules.

Usage:
    python build_git_history.py --category ndrappp
    python build_git_history.py --category ndrct --verbose
    python build_git_history.py --all --verbose
    python build_git_history.py --proofread --category ndrappp --verbose
    python build_git_history.py --category ndrappp --config config.yaml
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.logger import get_logger
from orchestrator.version_history_orchestrator import VersionHistoryOrchestrator


def _run_proofread(args, config, logger):
    """Run proofreading report generation."""
    import yaml
    from proofreading.report_generator import ProofreadingReportGenerator

    if not isinstance(config, dict):
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

    # Determine categories
    if args.all:
        categories = [
            k for k, v in config.get('git', {}).get('categories', {}).items()
            if v.get('enabled', False)
        ]
    else:
        categories = [args.category]

    # Create Anthropic client
    api_key = os.environ.get('ANTHROPIC_API_KEY') or config.get('anthropic', {}).get('api_key', '')
    if not api_key:
        print("Error: Anthropic API key required for proofreading.")
        print("Set ANTHROPIC_API_KEY environment variable or add to config.yaml")
        sys.exit(1)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    proof_config = config.get('proofreading', {})
    model = proof_config.get('model', 'claude-sonnet-4-5-20250929')
    max_tokens = proof_config.get('max_tokens', 2000)
    temperature = proof_config.get('temperature', 0.1)
    base_repo_dir = config.get('git', {}).get('repo_dir', '/Users/jerod/cDocs/refs/rules')

    for category in categories:
        repo_dir = f"{base_repo_dir}/{category}"
        report_dir = proof_config.get('report_dir') or repo_dir

        print(f"--- Proofreading: {category} ---")
        print(f"  Repo: {repo_dir}")
        print(f"  Model: {model}")
        print()

        generator = ProofreadingReportGenerator(
            anthropic_client=client,
            model=model,
            repo_dir=repo_dir,
            category=category,
            logger=logger,
            max_tokens=max_tokens,
            temperature=temperature,
            report_dir=report_dir,
        )

        report = generator.generate_report()
        meta = report['metadata']
        summary = report['summary']

        print()
        print("=" * 60)
        print(f"PROOFREADING COMPLETE: {category}")
        print("=" * 60)
        print(f"Rules reviewed:      {meta['rules_reviewed']}")
        print(f"Rules with findings: {meta['rules_with_findings']}")
        print(f"Errors:              {summary['total_errors']}")
        print(f"Warnings:            {summary['total_warnings']}")
        if meta.get('analysis_errors'):
            print(f"Analysis errors:     {meta['analysis_errors']}")
        print(f"Report:              {report_dir}/proofreading-report.md")
        print("=" * 60)
        print()


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
    parser.add_argument(
        '--proofread',
        action='store_true',
        help='Generate proofreading report for current rules (requires Anthropic API key)',
    )

    args = parser.parse_args()

    logger = get_logger(args.config, args.verbose)

    # Proofreading mode — separate path, no orchestrator needed
    if args.proofread:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        _run_proofread(args, config, logger)
        return

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

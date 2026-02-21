#!/usr/bin/env python3
"""
Build a git repository with full version history for ND Court Rules.

Usage:
    python build_git_history.py --category ndrappp
    python build_git_history.py --category ndrct --verbose
    python build_git_history.py --all --verbose
    python build_git_history.py --update --category ndrappp --verbose
    python build_git_history.py --update --all --verbose
    python build_git_history.py --proofread-mechanical --all --verbose
    python build_git_history.py --proofread-interactive --category ndrappp
    python build_git_history.py --proofread-api --category ndrappp --verbose
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


def _run_update(args, config, logger):
    """Run update mode: detect corrections and new amendments."""
    from orchestrator.update_orchestrator import UpdateOrchestrator

    # Determine categories
    combined_mode = args.all
    if args.all:
        categories = [
            k for k, v in config.get('git', {}).get('categories', {}).items()
            if v.get('enabled', False)
        ]
    else:
        categories = [args.category]

    if combined_mode:
        print(f"Updating combined repo: {', '.join(categories)}")
    else:
        print(f"Updating: {', '.join(categories)}")
    print(f"Config: {args.config}")
    print()

    orchestrator = UpdateOrchestrator(
        config_path=args.config,
        logger=logger,
    )

    has_errors = False

    try:
        for category in categories:
            print(f"--- Updating: {category} ---")
            stats = orchestrator.update_category(category, combined_mode=combined_mode)

            print()
            print("=" * 60)
            print(f"UPDATE COMPLETE: {category}")
            print("=" * 60)
            print(f"Unchanged:   {stats['skipped']}")
            print(f"Amended:     {stats['amended']}")
            print(f"New commits: {stats['new_commits']}")
            print(f"Duration:    {stats.get('duration_seconds', 0):.1f}s")

            if stats['errors']:
                has_errors = True
                print(f"Errors:      {len(stats['errors'])}")
                for err in stats['errors']:
                    print(f"  - {err}")

            print("=" * 60)
            print()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        if logger:
            logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        orchestrator.cleanup()

    if has_errors:
        sys.exit(1)


def _run_proofread_mechanical(args, config, logger):
    """Run local mechanical proofreading (no API calls)."""
    import yaml
    from proofreading.mechanical_checker import MechanicalChecker

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

    proof_config = config.get('proofreading', {})
    base_repo_dir = config.get('git', {}).get('repo_dir', '/Users/jerod/cDocs/refs/rules')

    for category in categories:
        repo_dir = f"{base_repo_dir}/{category}"
        report_dir = proof_config.get('report_dir') or repo_dir

        print(f"--- Mechanical proofreading: {category} ---")
        print(f"  Repo: {repo_dir}")
        print()

        checker = MechanicalChecker(
            repo_dir=repo_dir,
            category=category,
            logger=logger,
            report_dir=report_dir,
        )

        report = checker.run_checks()
        meta = report['metadata']
        summary = report['summary']

        print()
        print("=" * 60)
        print(f"MECHANICAL PROOFREADING COMPLETE: {category}")
        print("=" * 60)
        print(f"Rules reviewed:      {meta['rules_reviewed']}")
        print(f"Rules with findings: {meta['rules_with_findings']}")
        print(f"Errors:              {summary['total_errors']}")
        print(f"Warnings:            {summary['total_warnings']}")
        print(f"Report:              {report_dir}/mechanical-proofreading-report.md")
        print("=" * 60)
        print()


def _run_proofread_interactive(args, config, logger):
    """Generate files for interactive proofreading with Claude Code."""
    import yaml

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

    proof_config = config.get('proofreading', {})
    base_repo_dir = config.get('git', {}).get('repo_dir', '/Users/jerod/cDocs/refs/rules')

    CATEGORY_NAMES = {
        'ndrappp': 'North Dakota Rules of Appellate Procedure',
        'ndrct': 'North Dakota Rules of Court',
        'ndsupctadminr': 'North Dakota Supreme Court Administrative Rules',
        'ndsupctadminorder': 'North Dakota Supreme Court Administrative Orders',
        'ndrcivp': 'North Dakota Rules of Civil Procedure',
        'ndrcrimp': 'North Dakota Rules of Criminal Procedure',
        'ndrjuvp': 'North Dakota Rules of Juvenile Procedure',
        'ndrev': 'North Dakota Rules of Evidence',
        'local': 'North Dakota Local Court Rules',
        'admissiontopracticer': 'Rules for Admission to Practice Law',
        'ndrcontinuinglegaled': 'Rules for Continuing Legal Education',
        'ndrprofconduct': 'North Dakota Rules of Professional Conduct',
        'ndrlawyerdiscipl': 'North Dakota Rules for Lawyer Discipline',
        'ndstdsimposinglawyersanctions': 'Standards for Imposing Lawyer Sanctions',
        'ndcodejudconduct': 'North Dakota Code of Judicial Conduct',
        'rjudconductcomm': 'Rules of the Judicial Conduct Commission',
        'ndrprocr': 'North Dakota Rules of Procedure',
        'ndrlocalctpr': 'North Dakota Rules of Local Court Procedure',
        'rltdpracticeoflawbylawstudents': 'Rules for Limited Practice of Law by Law Students',
    }

    instructions = """\
# Proofreading Instructions

Review each rule below for errors. Report only genuine errors, not stylistic preferences.
These are published court rules — flag mistakes, not opinions.

Check for:
1. **Typos**: Misspellings, missing spaces, doubled words, wrong words
2. **Grammar**: Subject-verb agreement, sentence fragments, clear grammatical errors
3. **Citations**: Incorrect citation format, references to non-existent rules
4. **Cross-references**: Rule references that appear wrong
5. **Formatting**: Inconsistent numbering (e.g., jumps from (a) to (c)), missing subsection labels
6. **Substantive**: Contradictory provisions, ambiguous references, potential drafting errors

For each finding, note:
- The rule number
- Severity (ERROR for clear mistakes, WARNING for potential issues)
- The exact text containing the error
- What the error is
- Suggested correction (if obvious)

---

"""

    for category in categories:
        repo_dir = f"{base_repo_dir}/{category}"
        report_dir = proof_config.get('report_dir') or repo_dir
        category_name = CATEGORY_NAMES.get(category, category)

        # Load rules
        import glob as globmod
        pattern = str(Path(repo_dir) / 'rule-*.md')
        files = sorted(globmod.glob(pattern))
        if not files:
            print(f"  No rule files found in {repo_dir}")
            continue

        print(f"--- Interactive proofreading: {category} ({len(files)} rules) ---")

        if args.per_rule:
            # Per-rule mode: individual files
            out_dir = Path(report_dir) / 'proofread-interactive' / category
            out_dir.mkdir(parents=True, exist_ok=True)

            for filepath in files:
                filename = Path(filepath).name
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    continue

                out_path = out_dir / filename
                out_text = (
                    f"# Proofread: {category_name} — {filename}\n\n"
                    + instructions
                    + content
                )
                out_path.write_text(out_text, encoding='utf-8')

            print(f"  Wrote {len(files)} files to: {out_dir}/")
            print(f"  Usage: open files in Claude Code for interactive review")

        else:
            # Combined mode: one file per category
            out_path = Path(report_dir) / f'proofread-interactive-{category}.md'
            out_path.parent.mkdir(parents=True, exist_ok=True)

            parts = [
                f"# Proofread: {category_name}\n\n",
                instructions,
            ]

            for filepath in files:
                filename = Path(filepath).name
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    continue
                parts.append(f"\n---\n\n## File: {filename}\n\n")
                parts.append(content)
                parts.append("\n")

            out_path.write_text(''.join(parts), encoding='utf-8')
            print(f"  Wrote: {out_path}")
            print(f"  Usage: open this file in Claude Code for interactive review")

        print()


def _run_proofread_api(args, config, logger):
    """Run API-based proofreading report generation (legacy)."""
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
        description="Build git repository with ND Court Rules version history",
        epilog="""\
proofreading modes:
  --proofread-mechanical   Local-only checks: spelling (with legal dictionary),
                           doubled words, numbering gaps, unbalanced delimiters,
                           broken cross-references, whitespace issues, empty
                           sections, broken markdown, and inconsistent subsection
                           styles. No API calls, no cost. Produces markdown and
                           JSON reports in the category's repo directory.

  --proofread-interactive  Generates markdown files containing all rules with
                           proofreading instructions. Designed to be opened in
                           Claude Code for interactive review (subscription-based,
                           no per-call API cost). Use --per-rule to get one file
                           per rule instead of one combined file per category.

  --proofread-api          Sends each rule to Claude Sonnet via the Anthropic API
                           for automated analysis. Requires ANTHROPIC_API_KEY.
                           Produces markdown and JSON reports.

examples:
  %(prog)s --category ndrappp --verbose           Build one category
  %(prog)s --all --verbose                        Build all categories
  %(prog)s --update --all --verbose               Update all categories
  %(prog)s --proofread-mechanical --all --verbose  Mechanical proofread all
  %(prog)s --proofread-interactive --category ndrappp  Interactive proofread
  %(prog)s --proofread-api --category ndrappp --verbose  API proofread
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--category', '-k',
        default='ndrappp',
        help='Rule category to process (default: ndrappp)',
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Build combined repo with all enabled categories as subdirectories',
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
        '--update', '-u',
        action='store_true',
        help='Update existing repos: detect minor corrections and new amendments',
    )
    parser.add_argument(
        '--proofread-mechanical',
        action='store_true',
        help='Run local mechanical proofreading (spelling, formatting, cross-references)',
    )
    parser.add_argument(
        '--proofread-interactive',
        action='store_true',
        help='Generate proofreading prompts for interactive Claude Code review (no API cost)',
    )
    parser.add_argument(
        '--proofread-api',
        action='store_true',
        help='Run API-based proofreading with Claude Sonnet (requires ANTHROPIC_API_KEY)',
    )
    parser.add_argument(
        '--per-rule',
        action='store_true',
        help='With --proofread-interactive: generate individual per-rule files instead of one combined file',
    )

    args = parser.parse_args()

    logger = get_logger(args.config, args.verbose)

    # Update mode — separate path, uses UpdateOrchestrator
    if args.update:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        _run_update(args, config, logger)
        return

    # Proofreading modes — separate paths, no orchestrator needed
    if args.proofread_mechanical:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        _run_proofread_mechanical(args, config, logger)
        return

    if args.proofread_interactive:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        _run_proofread_interactive(args, config, logger)
        return

    if args.proofread_api:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        _run_proofread_api(args, config, logger)
        return

    orchestrator = VersionHistoryOrchestrator(
        config_path=args.config,
        logger=logger,
    )

    try:
        if args.all:
            # Combined mode: build one repo with all categories as subdirectories
            import yaml
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
            categories = [
                k for k, v in config.get('git', {}).get('categories', {}).items()
                if v.get('enabled', False)
            ]
            print(f"Building combined git repository: {', '.join(categories)}")
            print(f"Config: {args.config}")
            print()

            stats = orchestrator.build_combined_repository(
                categories=categories,
                force=args.force,
            )

            print()
            print("=" * 60)
            print("BUILD COMPLETE: combined repository")
            print("=" * 60)
            print(f"Categories:         {', '.join(categories)}")
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

        else:
            # Single-category mode: build standalone repo in subdirectory
            categories = [args.category]
            print(f"Building git history for category: {args.category}")
            print(f"Config: {args.config}")
            print()

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
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        orchestrator.cleanup()


if __name__ == '__main__':
    main()

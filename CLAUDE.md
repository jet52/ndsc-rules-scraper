# CLAUDE.md

## Project Overview

This scraper builds git repositories from North Dakota court rules. There are two build modes:

- **Combined mode** (`--all`): Builds a single git repo (`nd-court-rules`) at `git.repo_dir` with all categories as subdirectories (e.g., `ndrappp/rule-28.md`, `ndrct/rule-6-1.md`). Commits are interleaved chronologically across all categories.
- **Single-category mode** (`--category X`): Builds a standalone repo for one category in `{repo_dir}/{category}/` with rule files at the top level (e.g., `rule-28.md`).

## Key Commands

```bash
# Activate the venv (required)
source .venv/bin/activate

# Build combined repo with all enabled categories
python3 build_git_history.py --all --verbose

# Build a single standalone category repo
python3 build_git_history.py --category ndrappp --verbose

# Update combined repo (detect corrections & new amendments)
python3 build_git_history.py --update --all --verbose

# Update a single standalone category repo
python3 build_git_history.py --update --category ndrappp --verbose

# Mechanical proofreading (free, local only — spelling, formatting, cross-references)
python3 build_git_history.py --proofread-mechanical --category ndrappp --verbose
python3 build_git_history.py --proofread-mechanical --all --verbose

# Interactive proofreading (generates files to review with Claude Code — no API cost)
python3 build_git_history.py --proofread-interactive --category ndrappp
python3 build_git_history.py --proofread-interactive --all --per-rule

# API-based proofreading (requires ANTHROPIC_API_KEY, costs money)
python3 build_git_history.py --proofread-api --category ndrappp --verbose
python3 build_git_history.py --proofread-api --all --verbose

# Fix cross-reference links (dry run — report only)
python3 build_git_history.py --fix-crossrefs --all --verbose
python3 build_git_history.py --fix-crossrefs --category ndrappp --verbose

# Fix cross-reference links (apply — amends HEAD in each repo)
python3 build_git_history.py --fix-crossrefs --all --verbose --apply
```

Proofreading has three modes:
- **Mechanical** (`--proofread-mechanical`): Local-only checks using dictionary spell-check, regex patterns, and structural analysis. No API calls. Reports written to `{repo_dir}/{category}/mechanical-proofreading-report.md`.
- **Interactive** (`--proofread-interactive`): Generates markdown files with rule text and proofreading instructions, designed for review with Claude Code (subscription-based, no API cost). Use `--per-rule` to get individual files instead of one combined file per category.
- **API** (`--proofread-api`): Sends each rule to Claude Sonnet via Anthropic API. Requires `ANTHROPIC_API_KEY` env var. Reports written to `{repo_dir}/{category}/proofreading-report.md`.

## Architecture

The main entry point is `build_git_history.py`. It wires up the orchestrator which coordinates:

1. `version_history_orchestrator.py` — fetches the category index page, discovers rules, collects all versions across all rules, sorts globally by date, then commits chronologically
2. `version_history_extractor.py` — parses a rule's HTML page to extract the version history table (effective dates, version URLs, suffixes) and explanatory notes
3. `historical_version_fetcher.py` — downloads each version's HTML and converts to markdown
4. `committee_minutes_fetcher.py` — fetches committee meeting minutes PDFs for commit context
5. `commit_message_builder.py` — builds commit messages from explanatory notes and minutes (optionally uses Claude Haiku)
6. `git_version_manager.py` — manages git init, file writes, and commits with backdated author/committer dates
7. `update_orchestrator.py` — incremental update mode: compares current web content against local repos, amends commits for minor corrections, creates new commits for genuine amendments
8. `rule_link_fetcher.py` — shared module for extracting rule links from category index pages (used by both orchestrators)
9. `crossref_fixer.py` — post-processes rule files to convert absolute `/legal-resources/rules/` URLs to relative local links; resolves against actual files on disk

## Rule ID Formats

Different categories use different URL slug formats:
- `ndrappp`: pure numeric (`/ndrappp/28`)
- `ndrct`: hyphenated compound (`/ndrct/6-1` for Rule 6.1) and appendix slugs (`/ndrct/appendix-a`)
- `ndsupctadminr`: hyphenated compound (`/ndsupctadminr/24-1`)
- `ndsupctadminorder`: pure numeric (`/ndsupctadminorder/4`)
- `ndrcivp`: pure numeric (`/ndrcivp/4`) and dotted rules (`/ndrcivp/30-1` for Rule 30.1)
- `ndrcrimp`: pure numeric and dotted rules (`/ndrcrimp/5-1` for Rule 5.1)
- `ndrjuvp`: pure numeric and dotted rules (`/ndrjuvp/10-2` for Rule 10.2)
- `ndrev`: pure numeric, three-digit rule numbers (`/ndrev/501`, `/ndrev/1101`)
- `local`: varies by court
- `admissiontopracticer`: pure numeric
- `ndrcontinuinglegaled`: pure numeric
- `ndrprofconduct`: pure numeric and dotted rules
- `ndrlawyerdiscipl`: pure numeric and dotted rules
- `ndstdsimposinglawyersanctions`: pure numeric and dotted rules
- `ndcodejudconduct`: pure numeric and dotted rules
- `rjudconductcomm`: pure numeric
- `ndrprocr`: pure numeric
- `ndrlocalctpr`: pure numeric
- `rltdpracticeoflawbylawstudents`: pure numeric

Version suffixes are appended with a hyphen: `/ndrct/6-1-3` means version suffix "3" of base slug "6-1".

## Config

`config.yaml` has absolute paths specific to this machine. Categories are under `git.categories` with `enabled: true/false` flags. The `git.repo_dir` is the base directory. In combined mode (`--all`), the repo lives at `repo_dir` with category subdirectories. In single-category mode (`--category`), each category gets its own repo at `{repo_dir}/{category}/`.

## Conventions

- Python source lives in `src/` with packages: `scraper/`, `orchestrator/`, `git/`, `utils/`
- `sys.path.insert` in `build_git_history.py` adds `src/` to the path
- Use the `.venv` virtualenv, not system Python
- The scraper is rate-limited (`request_delay` in config) — don't remove the delays
- Output git repos are separate from this source repo

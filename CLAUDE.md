# CLAUDE.md

## Project Overview

This scraper builds git repositories from North Dakota court rules. Each rule category (appellate procedure, rules of court, admin rules, admin orders, civil procedure, criminal procedure, juvenile procedure, evidence) gets its own git repo where every historical version of every rule is a commit, dated to its effective date.

## Key Commands

```bash
# Activate the venv (required)
source .venv/bin/activate

# Build a single category
python3 build_git_history.py --category ndrappp --verbose

# Build all enabled categories
python3 build_git_history.py --all --verbose
```

## Architecture

The main entry point is `build_git_history.py`. It wires up the orchestrator which coordinates:

1. `version_history_orchestrator.py` — fetches the category index page, discovers rules, collects all versions across all rules, sorts globally by date, then commits chronologically
2. `version_history_extractor.py` — parses a rule's HTML page to extract the version history table (effective dates, version URLs, suffixes) and explanatory notes
3. `historical_version_fetcher.py` — downloads each version's HTML and converts to markdown
4. `committee_minutes_fetcher.py` — fetches committee meeting minutes PDFs for commit context
5. `commit_message_builder.py` — builds commit messages from explanatory notes and minutes (optionally uses Claude Haiku)
6. `git_version_manager.py` — manages git init, file writes, and commits with backdated author/committer dates

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

Version suffixes are appended with a hyphen: `/ndrct/6-1-3` means version suffix "3" of base slug "6-1".

## Config

`config.yaml` has absolute paths specific to this machine. Categories are under `git.categories` with `enabled: true/false` flags. The `git.repo_dir` is the base directory; each category gets a subdirectory (e.g., `{repo_dir}/ndrct/`).

## Conventions

- Python source lives in `src/` with packages: `scraper/`, `orchestrator/`, `git/`, `utils/`
- `sys.path.insert` in `build_git_history.py` adds `src/` to the path
- Use the `.venv` virtualenv, not system Python
- The scraper is rate-limited (`request_delay` in config) — don't remove the delays
- Output git repos are separate from this source repo

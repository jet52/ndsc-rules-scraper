# ND Court Rules Scraper

Scrapes North Dakota court rules from [ndcourts.gov](https://www.ndcourts.gov/legal-resources/rules) and builds git repositories where each rule is a markdown file and each historical version is a commit dated to its effective date.

## Rule Categories

| Category | Config Key | Description |
|----------|-----------|-------------|
| Appellate Procedure | `ndrappp` | 38 rules, ~219 versions |
| Rules of Court | `ndrct` | ~55 rules + 14 appendices, ~212 versions |
| Administrative Rules | `ndsupctadminr` | ~72 rules |
| Administrative Orders | `ndsupctadminorder` | 33 orders |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set the Anthropic API key for AI-generated commit messages (optional):

```bash
export ANTHROPIC_API_KEY="sk-..."
```

## Usage

Build a single category:

```bash
python3 build_git_history.py --category ndrappp --verbose
python3 build_git_history.py --category ndrct --verbose
```

Build all enabled categories:

```bash
python3 build_git_history.py --all --verbose
```

Force rebuild (re-initializes the git repo):

```bash
python3 build_git_history.py --category ndrappp --force
```

## Output

Each category gets its own git repository under the configured `git.repo_dir` (default: `/Users/jerod/cDocs/refs/rules/{category}/`). Inside:

- `rule-{number}.md` — one file per rule (e.g., `rule-28.md`, `rule-6.1.md`, `rule-appendix-a.md`)
- Git history with commits dated to each version's effective date
- Commit messages include explanatory notes and committee minutes context

Browse the history:

```bash
cd /path/to/rules/ndrappp
git log --oneline rule-28.md          # version history for one rule
git log -p rule-28.md                 # see diffs between versions
git log --before="2010-01-01" --oneline  # versions before a date
```

## How It Works

1. **Discovery** — Fetches the category index page and extracts links to each rule
2. **Version extraction** — For each rule, parses the version history table to find all historical versions with effective/obsolete dates
3. **Content fetching** — Downloads the HTML for each version and converts it to markdown
4. **Commit message building** — Extracts explanatory notes; optionally uses Claude to summarize committee minutes for richer commit messages
5. **Git construction** — Commits each version chronologically with `GIT_AUTHOR_DATE` set to the effective date

## Configuration

`config.yaml` controls everything. Key sections:

- `git.categories` — enable/disable categories, set base URLs
- `git.repo_dir` — base directory for output repositories
- `anthropic` — API key and model settings for commit messages
- `version_history.request_delay` — seconds between HTTP requests (be respectful)

## Project Structure

```
build_git_history.py              # CLI entry point
config.yaml                      # Configuration
src/
  orchestrator/
    version_history_orchestrator.py   # Main pipeline coordinator
  scraper/
    version_history_extractor.py      # Parses version tables from HTML
    historical_version_fetcher.py     # Downloads version content as markdown
    committee_minutes_fetcher.py      # Fetches committee meeting minutes
    commit_message_builder.py         # Builds rich commit messages
  git/
    git_version_manager.py            # Git repo init and commit operations
  utils/
    logger.py                         # Logging setup
```

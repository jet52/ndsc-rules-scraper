"""
Git Version Manager for ND Court Rules.
Creates and manages a git repository with chronological commits for rule versions.
"""

import os
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from scraper.historical_version_fetcher import RuleVersionContent
from scraper import explanatory_notes as xn


# Subject tail of a commit whose version the court dates 01/01/0001.
UNPUBLISHED_SUBJECT = "Current text (effective date not published)"

# Subject tail of a commit that only updates explanatory-note sidecars. Dated
# at OBSERVATION time (the note is cumulative and carries no date of its
# own), so readers of a rule's effective date must skip it — but it never
# touches a rule file, so get_rule_effective_date never sees it anyway.
NOTES_SUBJECT = "Explanatory notes"

class GitVersionManager:
    """Manages a git repository representing rule version history."""

    def __init__(
        self,
        repo_dir: str,
        author_name: str = "ND Courts System",
        author_email: str = "rules@ndcourts.gov",
        logger=None,
        category_prefix: Optional[str] = None,
    ):
        self.repo_dir = Path(repo_dir)
        self.author_name = author_name
        self.author_email = author_email
        self.logger = logger
        self.category_prefix = category_prefix

    def _rule_filename(self, rule_number: str) -> str:
        """Return the relative path for a rule file, respecting category_prefix."""
        base = f"rule-{rule_number}.md"
        if self.category_prefix:
            return f"{self.category_prefix}/{base}"
        return base

    def _notes_filename(self, rule_number: str) -> str:
        """Relative path of the rule's explanatory-note sidecar."""
        return xn.sidecar_relpath(rule_number, self.category_prefix)

    def get_notes_content(self, rule_number: str) -> Optional[str]:
        """The committed sidecar text, or None if the rule has none yet."""
        filepath = self.repo_dir / self._notes_filename(rule_number)
        if not filepath.exists():
            return None
        return filepath.read_bytes().decode('utf-8')

    def commit_notes(self, changes: List[tuple], category_label: str = "") -> bool:
        """Write and commit explanatory-note sidecars in ONE commit, dated now.

        ``changes`` is a list of ``(rule_number, sidecar_text, url)``. The
        sidecar is the court's cumulative note as observed on this run: it is
        not a version of the rule and has no effective date, so the commit is
        never backdated and touches no rule file. One commit per category per
        run keeps the mirror's history readable when every rule's note lands
        at once (the initial capture) and when the court's cycle amends
        dozens of notes on the same day.
        """
        if not changes:
            return True
        try:
            for rule_number, text, _url in changes:
                filename = self._notes_filename(rule_number)
                filepath = self.repo_dir / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(text, encoding='utf-8')
                self._run_git('add', filename)

            label = f" ({category_label})" if category_label else ""
            if len(changes) == 1:
                subject = f"Rule {changes[0][0]}: {NOTES_SUBJECT} updated{label}"
            else:
                subject = f"{NOTES_SUBJECT}: {len(changes)} rules updated{label}"
            body = ["The court's cumulative explanatory note for each rule, "
                    "verbatim, as published on ndcourts.gov at the time of this "
                    "commit.", ""]
            for rule_number, _text, url in changes:
                body.append(f"Rule {rule_number}" + (f" — {url}" if url else ""))
            message = subject + "\n\n" + "\n".join(body)
            ok = self._commit(message=message)
            if ok and self.logger:
                self.logger.info(
                    f"Committed explanatory notes for {len(changes)} rule(s){label}")
            return ok
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to commit explanatory notes: {e}")
            return False

    def initialize_repository(
        self,
        category_name: str = "ND Appellate Rules",
        combined: bool = False,
        category_names: Optional[dict] = None,
    ) -> bool:
        """
        Initialize a git repository for the rule category.

        Args:
            category_name: Human-readable name of the rule category
            combined: If True, create a combined repo README listing all categories
            category_names: Dict mapping category slugs to human-readable names (for combined mode)

        Returns:
            True if successful
        """
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        if (self.repo_dir / '.git').exists():
            if self.logger:
                self.logger.info(f"Git repository already exists at {self.repo_dir}")
            return True

        self._run_git('init')
        self._run_git('config', 'user.name', self.author_name)
        self._run_git('config', 'user.email', self.author_email)

        # Create README
        if combined and category_names:
            category_list = '\n'.join(
                f"- **`{slug}/`** — {name}" for slug, name in category_names.items()
            )
            readme_content = f"""# North Dakota Court Rules

This repository contains the North Dakota Court Rules with full version history.

Each rule category lives in its own subdirectory, with every rule stored as a
separate markdown file. Git history tracks how each rule has changed over time,
with commit dates matching the effective dates of each version.

## Categories

{category_list}

## Usage

```bash
# View history of a specific rule
git log --oneline ndrappp/rule-28.md

# See changes between versions
git log -p ndrct/rule-6-1.md

# View a rule as it existed at a specific date
git log --before="2010-12-31" --oneline ndrcivp/rule-4.md

# See all changes across all categories on a given date
git log --after="2020-02-28" --before="2020-03-02" --oneline
```

## Source

All rules sourced from the [North Dakota Courts website](https://www.ndcourts.gov/legal-resources/rules).
"""
        else:
            readme_content = f"""# {category_name}

This repository contains the North Dakota {category_name} with full version history.

Each rule is stored as a separate markdown file. Git history tracks how each rule
has changed over time, with commit dates matching the effective dates of each version.

## Usage

```bash
# View history of a specific rule
git log --oneline rule-28.md

# See changes between versions
git log -p rule-28.md

# View a rule as it existed at a specific date
git log --before="2010-12-31" --oneline rule-28.md
```

## Source

All rules sourced from the [North Dakota Courts website](https://www.ndcourts.gov/legal-resources/rules).
"""
        readme_path = self.repo_dir / 'README.md'
        readme_path.write_text(readme_content, encoding='utf-8')

        self._run_git('add', 'README.md')
        self._commit(
            message="Initialize repository",
            commit_date=None,
        )

        if self.logger:
            self.logger.info(f"Initialized git repository at {self.repo_dir}")

        return True

    def process_rule_history(
        self,
        rule_number: str,
        version_contents: List[RuleVersionContent],
    ) -> int:
        """
        Commit all versions of a rule chronologically.

        Args:
            rule_number: The rule number (e.g., "35")
            version_contents: List of RuleVersionContent, sorted oldest first

        Returns:
            Number of successful commits
        """
        commit_count = 0

        for content in version_contents:
            success = self.commit_rule_version(
                rule_number=rule_number,
                markdown_content=content.markdown,
                effective_date=content.effective_date,
                rule_title=content.rule_title,
                url=content.url,
                is_current=content.is_current,
            )
            if success:
                commit_count += 1

        if self.logger:
            self.logger.info(
                f"Committed {commit_count}/{len(version_contents)} versions for Rule {rule_number}"
            )

        return commit_count

    def commit_rule_version(
        self,
        rule_number: str,
        markdown_content: str,
        effective_date: Optional[date],
        rule_title: str,
        commit_body: str = "",
        url: str = "",
        is_current: bool = False,
    ) -> bool:
        """
        Write a rule version and commit it with the appropriate date.

        Args:
            rule_number: Rule number
            markdown_content: Markdown content for this version
            effective_date: When this version became effective
            rule_title: Title of the rule
            commit_body: Pre-built commit message body
            url: Source URL
            is_current: Whether this is the current version

        Returns:
            True if commit was successful
        """
        filename = self._rule_filename(rule_number)
        filepath = self.repo_dir / filename

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(markdown_content, encoding='utf-8')
            self._run_git('add', filename)

            # Build commit message. A None effective date is the court's own
            # "01/01/0001" placeholder: the commit is dated at scrape time and
            # its subject is the marker downstream readers key on
            # (get_rule_effective_date here; ingest_rules in ndlaw-mcp).
            if effective_date is None:
                subject = f"Rule {rule_number}: {UNPUBLISHED_SUBJECT}"
            else:
                date_str = effective_date.strftime('%B %d, %Y')
                subject = f"Rule {rule_number}: Update effective {date_str}"

            if commit_body:
                message = f"{subject}\n\n{commit_body}"
            else:
                status = "current" if is_current else "historical"
                body_parts = [rule_title]
                if url:
                    body_parts.append(f"Source: {url}")
                body_parts.append(f"Status: {status}")
                if effective_date is None:
                    body_parts.append("Effective date: not published (the court's "
                                      "version table shows 01/01/0001)")
                message = f"{subject}\n\n" + '\n'.join(body_parts)

            self._commit(message=message, commit_date=effective_date)

            if self.logger:
                self.logger.debug(
                    f"Committed Rule {rule_number} version effective {effective_date}"
                )
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Failed to commit Rule {rule_number} version {effective_date}: {e}"
                )
            return False

    def _commit(self, message: str, commit_date: Optional[date] = None) -> bool:
        """Create a git commit with optional date override."""
        env = os.environ.copy()
        env['GIT_AUTHOR_NAME'] = self.author_name
        env['GIT_COMMITTER_NAME'] = self.author_name
        env['GIT_AUTHOR_EMAIL'] = self.author_email
        env['GIT_COMMITTER_EMAIL'] = self.author_email

        if commit_date:
            # Set both author and committer date to noon on the effective date
            date_str = datetime.combine(commit_date, datetime.min.time().replace(hour=12)).strftime(
                '%Y-%m-%dT%H:%M:%S'
            )
            env['GIT_AUTHOR_DATE'] = date_str
            env['GIT_COMMITTER_DATE'] = date_str

        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message, '--allow-empty-message'],
                cwd=str(self.repo_dir),
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                if self.logger:
                    self.logger.warning(f"Git commit warning: {result.stderr.strip()}")
                # Check if it's just "nothing to commit"
                if 'nothing to commit' in result.stdout + result.stderr:
                    return True
                return False
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Git commit failed: {e}")
            return False

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        """Run a git command in the repository directory."""
        cmd = ['git'] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                if self.logger:
                    self.logger.warning(
                        f"Git command failed: {' '.join(cmd)}\n{result.stderr.strip()}"
                    )
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"Git command error: {' '.join(cmd)}: {e}")
            raise

    def get_current_file_content(self, rule_number: str) -> Optional[str]:
        """Read the current content of a rule file from disk.

        Returns:
            File content as string, or None if the file doesn't exist.
        """
        filepath = self.repo_dir / self._rule_filename(rule_number)
        if not filepath.exists():
            return None
        # Read raw bytes and decode without universal-newline translation.
        # read_text() collapses CRLF/CR to LF, which makes a byte-faithful
        # comparison against the scraped markdown report phantom "corrections"
        # for any stored file containing CRLF. Decoding bytes directly keeps
        # the comparison exact.
        return filepath.read_bytes().decode('utf-8')

    def get_rule_effective_date(self, rule_number: str) -> Optional[date]:
        """Get the effective date of the most recent commit for a rule file.

        The author date was set to the effective date at commit time, so
        we parse it from git log.

        Returns:
            The effective date, or None if the file has no commits.
        """
        filename = self._rule_filename(rule_number)
        # Walk newest-first and skip silent corrections: their author date is
        # the DETECTION date ("Recorded at the time the change was detected"),
        # not an effective date, so it never appears in the site's version
        # history. Reading it as the effective date wedged every silently
        # corrected rule: on 2026-08-28 Rules 3.1 and 11.2 (corrected
        # 2026-06-03) failed to anchor and their September 1, 2026 amendments
        # were skipped, while 3.4 and 8.3 logged "Unexpected state" (local date
        # newer than the web's) for the same reason.
        result = self._run_git('log', '--format=%aI%x09%s', '--', filename)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        date_str = None
        for line in result.stdout.splitlines():
            iso, _, subject = line.partition('\t')
            if 'Silent correction' in subject or UNPUBLISHED_SUBJECT in subject:
                # An unpublished-date commit is dated at SCRAPE time; it
                # carries no effective date either.
                continue
            date_str = iso.strip()
            break
        if not date_str:
            return None
        # Parse ISO 8601 date like "2024-03-01T12:00:00"
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            if self.logger:
                self.logger.warning(
                    f"Could not parse author date '{date_str}' for {filename}"
                )
            return None

    def amend_rule_version(self, rule_number: str, markdown_content: str) -> bool:
        """Amend the most recent commit touching a rule file with new content.

        Writes the new content, stages it, and amends the HEAD commit.
        Does NOT override GIT_AUTHOR_DATE/GIT_COMMITTER_DATE so the
        original effective date is preserved.

        Returns:
            True if the amend succeeded.
        """
        filename = self._rule_filename(rule_number)
        filepath = self.repo_dir / filename

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(markdown_content, encoding='utf-8')
            self._run_git('add', filename)

            env = os.environ.copy()
            env['GIT_AUTHOR_NAME'] = self.author_name
            env['GIT_COMMITTER_NAME'] = self.author_name
            env['GIT_AUTHOR_EMAIL'] = self.author_email
            env['GIT_COMMITTER_EMAIL'] = self.author_email

            result = subprocess.run(
                ['git', 'commit', '--amend', '--no-edit'],
                cwd=str(self.repo_dir),
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                if self.logger:
                    self.logger.error(
                        f"Amend failed for Rule {rule_number}: {result.stderr.strip()}"
                    )
                return False
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Amend error for Rule {rule_number}: {e}")
            return False

    def commit_correction(self, rule_number: str, markdown_content: str) -> bool:
        """Commit a silent same-date correction as a NEW commit dated now.

        Unlike amend_rule_version (which rewrites HEAD and, in combined mode,
        can fold the change into an unrelated rule's commit), this stages only
        the corrected rule file and creates its own commit at the real
        observation time. The rule's effective date is unchanged, so the commit
        is intentionally not backdated.

        Returns:
            True if the commit succeeded.
        """
        filename = self._rule_filename(rule_number)
        filepath = self.repo_dir / filename

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(markdown_content, encoding='utf-8')
            self._run_git('add', filename)

            message = (
                f"Rule {rule_number}: Silent correction (effective date unchanged)\n\n"
                "Text correction published by the court without a new effective "
                "date. Recorded at the time the change was detected."
            )
            # No commit_date override -> recorded at the real detection time.
            return self._commit(message=message)

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Correction commit error for Rule {rule_number}: {e}"
                )
            return False

    def amend_files(self, file_changes: dict) -> bool:
        """Amend HEAD with updated file contents.

        Args:
            file_changes: Dict mapping relative paths to new file content.

        Returns:
            True if the amend succeeded.
        """
        try:
            for rel_path, content in file_changes.items():
                filepath = self.repo_dir / rel_path
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content, encoding='utf-8')
                self._run_git('add', rel_path)

            env = os.environ.copy()
            env['GIT_AUTHOR_NAME'] = self.author_name
            env['GIT_COMMITTER_NAME'] = self.author_name
            env['GIT_AUTHOR_EMAIL'] = self.author_email
            env['GIT_COMMITTER_EMAIL'] = self.author_email

            result = subprocess.run(
                ['git', 'commit', '--amend', '--no-edit'],
                cwd=str(self.repo_dir),
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                if self.logger:
                    self.logger.error(f"Amend files failed: {result.stderr.strip()}")
                return False
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Amend files error: {e}")
            return False

    def restore_rule_file(self, rule_number: str) -> None:
        """Restore a rule file to its HEAD state (undo uncommitted changes)."""
        filename = self._rule_filename(rule_number)
        self._run_git('checkout', 'HEAD', '--', filename)

    def get_commit_count(self) -> int:
        """Get the total number of commits in the repository."""
        result = self._run_git('rev-list', '--count', 'HEAD')
        if result.returncode == 0:
            return int(result.stdout.strip())
        return 0

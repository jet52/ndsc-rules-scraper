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


class GitVersionManager:
    """Manages a git repository representing rule version history."""

    def __init__(
        self,
        repo_dir: str,
        author_name: str = "ND Courts System",
        author_email: str = "rules@ndcourts.gov",
        logger=None,
    ):
        self.repo_dir = Path(repo_dir)
        self.author_name = author_name
        self.author_email = author_email
        self.logger = logger

    def initialize_repository(self, category_name: str = "ND Appellate Rules") -> bool:
        """
        Initialize a git repository for the rule category.

        Args:
            category_name: Human-readable name of the rule category

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
        filename = f"rule-{rule_number}.md"

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
        effective_date: date,
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
        filename = f"rule-{rule_number}.md"
        filepath = self.repo_dir / filename

        try:
            filepath.write_text(markdown_content, encoding='utf-8')
            self._run_git('add', filename)

            # Build commit message
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

    def get_commit_count(self) -> int:
        """Get the total number of commits in the repository."""
        result = self._run_git('rev-list', '--count', 'HEAD')
        if result.returncode == 0:
            return int(result.stdout.strip())
        return 0

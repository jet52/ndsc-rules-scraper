"""
Proofreading Report Generator for ND Court Rules.
Reads current rule markdown from git repos and uses Claude to identify errors.
Produces markdown and JSON reports for submission to the court.
"""

import glob
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ProofreadingReportGenerator:
    """Generates proofreading reports by analyzing rule markdown with Claude."""

    CATEGORY_NAMES = {
        'ndrappp': 'North Dakota Rules of Appellate Procedure',
        'ndrct': 'North Dakota Rules of Court',
        'ndsupctadminr': 'North Dakota Supreme Court Administrative Rules',
        'ndsupctadminorder': 'North Dakota Supreme Court Administrative Orders',
        'ndrcivp': 'North Dakota Rules of Civil Procedure',
        'ndrcrimp': 'North Dakota Rules of Criminal Procedure',
        'ndrjuvp': 'North Dakota Rules of Juvenile Procedure',
        'ndrev': 'North Dakota Rules of Evidence',
    }

    def __init__(self, anthropic_client, model: str, repo_dir: str,
                 category: str, logger=None, max_tokens: int = 2000,
                 temperature: float = 0.1, report_dir: Optional[str] = None):
        self.client = anthropic_client
        self.model = model
        self.repo_dir = repo_dir
        self.category = category
        self.logger = logger
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.report_dir = report_dir or repo_dir
        self.category_name = self.CATEGORY_NAMES.get(category, category)

    def generate_report(self) -> dict:
        """Read all rule-*.md files, analyze each, produce report."""
        rules = self._load_rules()
        if not rules:
            if self.logger:
                self.logger.warning(f"No rule files found in {self.repo_dir}")
            return {
                'metadata': {'rules_reviewed': 0, 'rules_with_findings': 0},
                'summary': {'total_errors': 0, 'total_warnings': 0},
                'findings': [],
                'per_rule': [],
            }

        if self.logger:
            self.logger.info(f"Found {len(rules)} rule files to analyze")

        findings = []
        for i, (rule_file, content) in enumerate(rules):
            if self.logger:
                self.logger.info(f"Analyzing {rule_file} ({i + 1}/{len(rules)})")
            result = self._analyze_rule(rule_file, content)
            findings.append(result)

        report = self._compile_report(findings)
        self._write_markdown_report(report)
        self._write_json_report(report)
        return report

    def _load_rules(self) -> List[Tuple[str, str]]:
        """Load all rule-*.md files from the repo directory."""
        pattern = str(Path(self.repo_dir) / 'rule-*.md')
        files = sorted(glob.glob(pattern))
        rules = []
        for filepath in files:
            filename = Path(filepath).name
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.strip():
                rules.append((filename, content))
        return rules

    def _analyze_rule(self, filename: str, content: str) -> dict:
        """Send rule to Claude for structured analysis. Returns findings dict."""
        tools = [{
            "name": "report_findings",
            "description": "Report proofreading findings for a court rule.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "has_issues": {
                        "type": "boolean",
                        "description": "Whether any issues were found",
                    },
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "severity": {
                                    "type": "string",
                                    "enum": ["ERROR", "WARNING"],
                                    "description": "ERROR for clear mistakes, WARNING for potential issues",
                                },
                                "category": {
                                    "type": "string",
                                    "enum": ["typo", "grammar", "citation", "cross-reference",
                                             "formatting", "substantive"],
                                },
                                "quote": {
                                    "type": "string",
                                    "description": "The exact text containing the error",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What the error is",
                                },
                                "suggestion": {
                                    "type": "string",
                                    "description": "Suggested correction, if obvious",
                                },
                            },
                            "required": ["severity", "category", "quote", "description"],
                        },
                    },
                },
                "required": ["has_issues", "findings"],
            },
        }]

        prompt = f"""You are proofreading a published North Dakota court rule.
Your job is to identify clear errors for a report to the court.

IMPORTANT: Report only genuine errors and strong concerns, NOT stylistic preferences.
These are published court rules — flag mistakes, not opinions.

Check for:
1. TYPOS: Misspellings, missing spaces, doubled words, wrong words
2. GRAMMAR: Subject-verb agreement, sentence fragments, clear grammatical errors
3. CITATIONS: Incorrect citation format, references to non-existent rules
4. CROSS-REFERENCES: Rule references that appear wrong
5. FORMATTING: Inconsistent numbering (e.g., jumps from (a) to (c)), missing subsection labels
6. SUBSTANTIVE: Contradictory provisions, ambiguous "this" without antecedent, potential drafting errors

Use the report_findings tool to report your results. If the rule has no issues, call the tool with has_issues=false and an empty findings array.

RULE FILE: {filename}

RULE TEXT:
{content}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                tools=tools,
                tool_choice={"type": "tool", "name": "report_findings"},
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract tool use result
            for block in response.content:
                if block.type == "tool_use" and block.name == "report_findings":
                    tool_input = block.input
                    return {
                        'filename': filename,
                        'rule_number': self._filename_to_rule_number(filename),
                        'has_issues': tool_input.get('has_issues', False),
                        'findings': tool_input.get('findings', []),
                    }

            # Fallback if no tool use found
            return self._empty_result(filename)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error analyzing {filename}: {e}")
            return self._empty_result(filename, error=str(e))

    def _empty_result(self, filename: str, error: Optional[str] = None) -> dict:
        result = {
            'filename': filename,
            'rule_number': self._filename_to_rule_number(filename),
            'has_issues': False,
            'findings': [],
        }
        if error:
            result['error'] = error
        return result

    def _filename_to_rule_number(self, filename: str) -> str:
        """Convert 'rule-6-1.md' to '6.1', 'rule-appendix-a.md' to 'appendix-a'."""
        stem = filename.replace('rule-', '').replace('.md', '')
        if stem.startswith('appendix'):
            return stem
        # Convert hyphens back to dots for numeric rules: "6-1" → "6.1"
        parts = stem.split('-')
        if all(p.isdigit() for p in parts):
            return '.'.join(parts)
        return stem

    def _compile_report(self, findings: List[dict]) -> dict:
        """Aggregate findings into structured report."""
        all_findings = []
        rules_with_findings = 0
        total_errors = 0
        total_warnings = 0

        for result in findings:
            if result['has_issues']:
                rules_with_findings += 1
            for f in result.get('findings', []):
                finding = {
                    'rule_number': result['rule_number'],
                    'filename': result['filename'],
                    **f,
                }
                all_findings.append(finding)
                if f.get('severity') == 'ERROR':
                    total_errors += 1
                else:
                    total_warnings += 1

        errors = [r for r in findings if r.get('error')]

        return {
            'metadata': {
                'category': self.category,
                'category_name': self.category_name,
                'generated_at': datetime.now().isoformat(),
                'model': self.model,
                'rules_reviewed': len(findings),
                'rules_with_findings': rules_with_findings,
                'analysis_errors': len(errors),
            },
            'summary': {
                'total_errors': total_errors,
                'total_warnings': total_warnings,
            },
            'findings': all_findings,
            'per_rule': findings,
        }

    def _write_markdown_report(self, report: dict):
        """Write human-readable markdown report."""
        meta = report['metadata']
        summary = report['summary']
        lines = [
            f"# Proofreading Report: {meta['category_name']}",
            "",
            f"Generated: {meta['generated_at'][:10]}",
            f"Model: {meta['model']}",
            f"Rules reviewed: {meta['rules_reviewed']}",
            f"Rules with findings: {meta['rules_with_findings']}",
            f"Total findings: {summary['total_errors'] + summary['total_warnings']}"
            f" ({summary['total_errors']} errors, {summary['total_warnings']} warnings)",
            "",
        ]

        if meta.get('analysis_errors'):
            lines.append(f"Analysis errors: {meta['analysis_errors']}")
            lines.append("")

        # Summary table
        rules_with_issues = [r for r in report['per_rule'] if r['has_issues']]
        if rules_with_issues:
            lines.append("## Summary")
            lines.append("")
            lines.append("| Rule | Errors | Warnings |")
            lines.append("|------|--------|----------|")
            for r in rules_with_issues:
                errors = sum(1 for f in r['findings'] if f.get('severity') == 'ERROR')
                warnings = sum(1 for f in r['findings'] if f.get('severity') == 'WARNING')
                lines.append(f"| Rule {r['rule_number']} | {errors} | {warnings} |")
            lines.append("")

        # Detailed findings
        if report['findings']:
            lines.append("## Findings")
            lines.append("")

            current_rule = None
            for f in report['findings']:
                if f['rule_number'] != current_rule:
                    current_rule = f['rule_number']
                    # Find rule title from per_rule data
                    lines.append(f"### Rule {current_rule}")
                    lines.append("")

                severity = f.get('severity', 'WARNING')
                category = f.get('category', 'unknown')
                lines.append(f"**{severity}** ({category}): {f.get('description', '')}")
                if f.get('quote'):
                    lines.append(f"> {f['quote']}")
                if f.get('suggestion'):
                    lines.append(f"")
                    lines.append(f"Suggested: {f['suggestion']}")
                lines.append("")
        else:
            lines.append("## No issues found")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*This report was generated by automated analysis using Claude AI.")
        lines.append("All findings should be verified by a human reviewer before submission.*")
        lines.append("")

        report_path = Path(self.report_dir) / 'proofreading-report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('\n'.join(lines), encoding='utf-8')

        if self.logger:
            self.logger.info(f"Markdown report written to {report_path}")

    def _write_json_report(self, report: dict):
        """Write machine-readable JSON report."""
        # Strip per_rule from JSON output (redundant with findings)
        json_report = {
            'metadata': report['metadata'],
            'summary': report['summary'],
            'findings': report['findings'],
        }

        report_path = Path(self.report_dir) / 'proofreading-report.json'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(json_report, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )

        if self.logger:
            self.logger.info(f"JSON report written to {report_path}")

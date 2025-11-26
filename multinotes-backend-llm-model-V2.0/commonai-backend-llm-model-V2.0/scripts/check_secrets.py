#!/usr/bin/env python
"""
Secret Detection Script for Pre-commit Hook.

This script scans files for potential secrets and sensitive data
that should not be committed to version control.

Usage:
    python scripts/check_secrets.py file1.py file2.py ...
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Pattern


# =============================================================================
# Secret Patterns
# =============================================================================

# Patterns that indicate potential secrets
SECRET_PATTERNS: List[Tuple[str, Pattern, str]] = [
    # API Keys
    ('AWS Access Key', re.compile(r'AKIA[0-9A-Z]{16}'), 'AWS access key detected'),
    ('AWS Secret Key', re.compile(r'(?i)aws_secret_access_key\s*=\s*["\'][A-Za-z0-9/+=]{40}["\']'), 'AWS secret key detected'),
    ('Google API Key', re.compile(r'AIza[0-9A-Za-z_-]{35}'), 'Google API key detected'),
    ('Stripe Live Key', re.compile(r'sk_live_[0-9a-zA-Z]{24,}'), 'Stripe live key detected'),
    ('Stripe Test Key', re.compile(r'sk_test_[0-9a-zA-Z]{24,}'), 'Stripe test key (consider using env var)'),
    ('Razorpay Key', re.compile(r'rzp_(live|test)_[0-9a-zA-Z]{14,}'), 'Razorpay key detected'),

    # OAuth Tokens
    ('GitHub Token', re.compile(r'ghp_[0-9a-zA-Z]{36}'), 'GitHub personal access token detected'),
    ('GitHub OAuth', re.compile(r'gho_[0-9a-zA-Z]{36}'), 'GitHub OAuth token detected'),
    ('GitLab Token', re.compile(r'glpat-[0-9a-zA-Z\-]{20,}'), 'GitLab personal access token detected'),

    # Database Connection Strings
    ('MySQL Connection', re.compile(r'mysql://[^:]+:[^@]+@[^\s]+'), 'MySQL connection string with credentials'),
    ('PostgreSQL Connection', re.compile(r'postgres://[^:]+:[^@]+@[^\s]+'), 'PostgreSQL connection string with credentials'),
    ('MongoDB Connection', re.compile(r'mongodb(\+srv)?://[^:]+:[^@]+@[^\s]+'), 'MongoDB connection string with credentials'),
    ('Redis Connection', re.compile(r'redis://:[^@]+@[^\s]+'), 'Redis connection string with password'),

    # OpenAI/LLM Keys
    ('OpenAI API Key', re.compile(r'sk-[a-zA-Z0-9]{48,}'), 'OpenAI API key detected'),
    ('Anthropic API Key', re.compile(r'sk-ant-[a-zA-Z0-9]{40,}'), 'Anthropic API key detected'),

    # Generic Patterns
    ('Generic API Key', re.compile(r'(?i)api[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9]{20,}["\']'), 'Hardcoded API key'),
    ('Generic Secret', re.compile(r'(?i)secret[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9!@#$%^&*]{16,}["\']'), 'Hardcoded secret key'),
    ('Generic Password', re.compile(r'(?i)password\s*[=:]\s*["\'][^${\s][^"\']{6,}["\']'), 'Hardcoded password'),
    ('Generic Token', re.compile(r'(?i)(access[_-]?token|auth[_-]?token)\s*[=:]\s*["\'][a-zA-Z0-9]{20,}["\']'), 'Hardcoded token'),

    # Private Keys
    ('RSA Private Key', re.compile(r'-----BEGIN RSA PRIVATE KEY-----'), 'RSA private key detected'),
    ('DSA Private Key', re.compile(r'-----BEGIN DSA PRIVATE KEY-----'), 'DSA private key detected'),
    ('EC Private Key', re.compile(r'-----BEGIN EC PRIVATE KEY-----'), 'EC private key detected'),
    ('OpenSSH Private Key', re.compile(r'-----BEGIN OPENSSH PRIVATE KEY-----'), 'OpenSSH private key detected'),
    ('PGP Private Key', re.compile(r'-----BEGIN PGP PRIVATE KEY BLOCK-----'), 'PGP private key detected'),

    # JWT Tokens (longer ones that are likely real)
    ('JWT Token', re.compile(r'eyJ[a-zA-Z0-9_-]{50,}\.[a-zA-Z0-9_-]{50,}\.[a-zA-Z0-9_-]{50,}'), 'JWT token detected'),
]

# File patterns to exclude from scanning
EXCLUDE_PATTERNS = [
    re.compile(r'\.min\.js$'),
    re.compile(r'package-lock\.json$'),
    re.compile(r'yarn\.lock$'),
    re.compile(r'\.pyc$'),
    re.compile(r'__pycache__'),
    re.compile(r'\.git/'),
    re.compile(r'node_modules/'),
    re.compile(r'\.env\.example$'),
    re.compile(r'\.secrets\.baseline$'),
]

# Lines containing these patterns are likely false positives
FALSE_POSITIVE_PATTERNS = [
    re.compile(r'#.*noqa'),
    re.compile(r'#.*nosec'),
    re.compile(r'#.*pragma:\s*allowlist'),
    re.compile(r'os\.environ\.get'),
    re.compile(r'os\.getenv'),
    re.compile(r'config\['),
    re.compile(r'settings\.'),
    re.compile(r'\$\{'),
    re.compile(r'%\('),
    re.compile(r'example'),
    re.compile(r'placeholder'),
    re.compile(r'xxx+', re.IGNORECASE),
    re.compile(r'your[_-]?api[_-]?key', re.IGNORECASE),
    re.compile(r'test[_-]?key', re.IGNORECASE),
    re.compile(r'dummy', re.IGNORECASE),
]


# =============================================================================
# Scanner
# =============================================================================

class SecretScanner:
    """Scan files for potential secrets."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings = []

    def should_exclude_file(self, filepath: str) -> bool:
        """Check if file should be excluded from scanning."""
        for pattern in EXCLUDE_PATTERNS:
            if pattern.search(filepath):
                return True
        return False

    def is_false_positive(self, line: str) -> bool:
        """Check if line is likely a false positive."""
        for pattern in FALSE_POSITIVE_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def scan_file(self, filepath: str) -> List[dict]:
        """
        Scan a single file for secrets.

        Args:
            filepath: Path to file to scan

        Returns:
            List of findings
        """
        if self.should_exclude_file(filepath):
            if self.verbose:
                print(f"Skipping excluded file: {filepath}")
            return []

        findings = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip false positives
                    if self.is_false_positive(line):
                        continue

                    for name, pattern, message in SECRET_PATTERNS:
                        matches = pattern.findall(line)
                        if matches:
                            findings.append({
                                'file': filepath,
                                'line': line_num,
                                'type': name,
                                'message': message,
                                'snippet': self._mask_secret(line.strip(), matches[0]),
                            })

        except Exception as e:
            if self.verbose:
                print(f"Error scanning {filepath}: {e}")

        return findings

    def _mask_secret(self, line: str, secret: str) -> str:
        """Mask the secret in the line for display."""
        if len(secret) > 10:
            masked = secret[:4] + '*' * (len(secret) - 8) + secret[-4:]
            return line.replace(secret, masked)
        return line.replace(secret, '*' * len(secret))

    def scan_files(self, filepaths: List[str]) -> List[dict]:
        """
        Scan multiple files for secrets.

        Args:
            filepaths: List of file paths to scan

        Returns:
            List of all findings
        """
        all_findings = []

        for filepath in filepaths:
            path = Path(filepath)
            if path.exists() and path.is_file():
                findings = self.scan_file(filepath)
                all_findings.extend(findings)

        self.findings = all_findings
        return all_findings

    def report(self) -> str:
        """Generate a report of findings."""
        if not self.findings:
            return "No secrets detected."

        lines = ["Secret Detection Report", "=" * 50, ""]

        for finding in self.findings:
            lines.append(f"File: {finding['file']}:{finding['line']}")
            lines.append(f"Type: {finding['type']}")
            lines.append(f"Message: {finding['message']}")
            lines.append(f"Snippet: {finding['snippet']}")
            lines.append("")

        lines.append(f"Total findings: {len(self.findings)}")

        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Scan files for potential secrets and sensitive data.'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to scan'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--baseline',
        help='Path to baseline file for known false positives'
    )

    args = parser.parse_args()

    if not args.files:
        print("No files specified.")
        sys.exit(0)

    scanner = SecretScanner(verbose=args.verbose)
    findings = scanner.scan_files(args.files)

    if findings:
        print(scanner.report())
        print("\n❌ Secret detection failed!")
        print("Please remove or use environment variables for sensitive data.")
        print("Add '# noqa' or '# pragma: allowlist secret' to ignore false positives.")
        sys.exit(1)
    else:
        if args.verbose:
            print("✓ No secrets detected.")
        sys.exit(0)


if __name__ == '__main__':
    main()

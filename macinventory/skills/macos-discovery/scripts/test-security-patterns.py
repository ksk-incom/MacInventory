#!/usr/bin/env python3
"""Test security patterns against sample config files with fake secrets.

Usage:
    python test-security-patterns.py              # Run all tests
    python test-security-patterns.py --verbose    # Show detailed output
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# Sample config files with FAKE secrets for testing
# These are synthetic test data, not real credentials
SAMPLE_CONFIGS = {
    "shell_config": """
# Sample .zshrc with fake secrets
export PATH="/usr/local/bin:$PATH"

# Fake API keys for testing pattern matching
export OPENAI_API_KEY="sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890AB"
export ANTHROPIC_API_KEY="sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Fake GitHub tokens
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export GH_TOKEN="gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Fake AWS credentials
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Generic patterns
API_KEY=fake_api_key_12345678901234567890
password=mysupersecretpassword
secret=this_is_a_test_secret
token=some_fake_token_value_12345678901234567890

# Bearer token in header
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token
""",

    "json_config": """
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "connection_string": "postgresql://myuser:secretpassword123@localhost:5432/mydb"
  },
  "redis": {
    "url": "redis://:redispassword@localhost:6379"
  },
  "api": {
    "stripe_key": "sk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "openai_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890AB"
  },
  "auth": {
    "secret": "jwt_secret_value_here",
    "api_key": "fake_api_key_for_testing_12345678901234"
  }
}
""",

    "yaml_config": """
# Sample YAML config with fake secrets
database:
  host: localhost
  port: 5432
  connection_string: mongodb+srv://user:mongopassword@cluster.mongodb.net/

api:
  github_token: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  slack_token: xoxb-fake-token-value-123

credentials:
  api_key: fake_api_key_12345678901234567890
  password: test_password_value
  token: auth_token_fake_value_12345678901234567890

mysql:
  url: mysql://root:mysqlpass@localhost:3306/db
""",

    "env_file": """
# Sample .env file with fake secrets
DATABASE_URL=postgresql://user:dbpassword@host:5432/db
REDIS_URL=redis://:redispass@localhost:6379
OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890AB
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
API_KEY=fake_key_12345678901234567890
SECRET_KEY=django_secret_key_fake_value
""",

    "private_key_file": """
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtest...
This is a fake private key for testing detection
-----END RSA PRIVATE KEY-----
""",

    "ssh_config_safe": """
# Sample SSH config - should NOT be redacted (no secrets)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519

Host myserver
    HostName 192.168.1.100
    User admin
    Port 22
    ForwardAgent yes
""",
}


def load_security_patterns() -> Dict:
    """Load security patterns from YAML file."""
    script_dir = Path(__file__).parent.resolve()

    possible_paths = [
        script_dir.parent.parent.parent / 'data' / 'security-patterns.yaml',
        Path.cwd() / 'macinventory' / 'data' / 'security-patterns.yaml',
        Path.cwd() / 'data' / 'security-patterns.yaml',
    ]

    for path in possible_paths:
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(
        f"security-patterns.yaml not found. Tried: {possible_paths}"
    )


def apply_filter_patterns(content: str, patterns: List[Dict]) -> Tuple[str, List[str]]:
    """Apply filter patterns to content, return filtered content and list of matches."""
    matches = []
    filtered = content

    for pattern_def in patterns:
        name = pattern_def['name']
        pattern = pattern_def['pattern']
        replacement = pattern_def['replacement']

        try:
            regex = re.compile(pattern)
            found = regex.findall(content)
            if found:
                matches.append(f"{name}: {len(found) if isinstance(found, list) else 1} match(es)")
                filtered = regex.sub(replacement, filtered)
        except re.error as e:
            matches.append(f"{name}: REGEX ERROR - {e}")

    return filtered, matches


def test_pattern_matching(verbose: bool = False) -> Tuple[int, int]:
    """Test all patterns against sample configs. Returns (passed, failed)."""
    try:
        patterns = load_security_patterns()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    filter_patterns = patterns.get('filter_patterns', [])

    passed = 0
    failed = 0

    print("=" * 70)
    print("SECURITY PATTERN TESTS")
    print("=" * 70)

    for config_name, content in SAMPLE_CONFIGS.items():
        print(f"\n--- Testing: {config_name} ---")

        filtered, matches = apply_filter_patterns(content, filter_patterns)

        if matches:
            passed += 1
            print(f"  ✓ Found and filtered {len(matches)} pattern type(s):")
            if verbose:
                for match in matches:
                    print(f"    - {match}")
        else:
            # SSH config should have no matches (contains no secrets)
            if config_name == "ssh_config_safe":
                passed += 1
                print("  ✓ Correctly found no secrets (safe config)")
            else:
                failed += 1
                print("  ✗ No patterns matched (expected some matches)")

        # Verify structure is preserved (basic check)
        if config_name == "json_config":
            # Check JSON still has valid structure markers
            if '{' in filtered and '}' in filtered and ':' in filtered:
                if verbose:
                    print("    ✓ JSON structure preserved")
            else:
                failed += 1
                print("  ✗ JSON structure may be broken")

        if config_name == "yaml_config":
            # Check YAML still has colons (key: value)
            if ':' in filtered:
                if verbose:
                    print("    ✓ YAML structure preserved")
            else:
                failed += 1
                print("  ✗ YAML structure may be broken")

        # Show filtered output in verbose mode
        if verbose:
            print("\n  Filtered output (first 500 chars):")
            preview = filtered[:500].replace('\n', '\n    ')
            print(f"    {preview}")
            if len(filtered) > 500:
                print(f"    ... ({len(filtered) - 500} more chars)")

    return passed, failed


def test_specific_patterns(verbose: bool = False) -> Tuple[int, int]:
    """Test specific pattern matches."""
    patterns = load_security_patterns()
    filter_patterns = patterns.get('filter_patterns', [])

    print("\n" + "=" * 70)
    print("SPECIFIC PATTERN VALIDATION")
    print("=" * 70)

    passed = 0
    failed = 0

    # Test cases: (pattern_name, test_string, should_match)
    test_cases = [
        ("github_pat", "ghp_123456789012345678901234567890123456", True),  # Exactly 36 chars after ghp_
        ("github_pat", "ghp_short", False),  # Too short
        ("openai_key", "sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890AB", True),
        ("anthropic_key", "sk-ant-" + "x" * 80, True),
        ("aws_access_key", "AKIAIOSFODNN7EXAMPLE", True),
        ("aws_access_key", "AKIA123", False),  # Too short
        ("stripe_key", "sk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxx", True),
        ("slack_token", "xoxb-123-456-abc", True),
        ("postgres_url", "postgresql://user:pass@host:5432/db", True),
        ("private_key_header", "-----BEGIN RSA PRIVATE KEY-----", True),
        ("private_key_header", "-----BEGIN OPENSSH PRIVATE KEY-----", True),
        ("bearer_token", "Bearer eyJhbGciOiJIUzI1NiJ9.test", True),
        ("generic_api_key", "api_key=abcd1234567890123456", True),
    ]

    for pattern_name, test_string, should_match in test_cases:
        # Find the pattern
        pattern_def = next(
            (p for p in filter_patterns if p['name'] == pattern_name),
            None
        )

        if not pattern_def:
            print(f"  ? {pattern_name}: Pattern not found in security-patterns.yaml")
            failed += 1
            continue

        try:
            regex = re.compile(pattern_def['pattern'])
            matched = bool(regex.search(test_string))

            if matched == should_match:
                passed += 1
                status = "matched" if matched else "no match"
                if verbose:
                    print(f"  ✓ {pattern_name}: {status} (expected)")
            else:
                failed += 1
                status = "matched" if matched else "no match"
                expected = "match" if should_match else "no match"
                print(f"  ✗ {pattern_name}: {status} (expected {expected})")
                if verbose:
                    print(f"    Pattern: {pattern_def['pattern']}")
                    print(f"    Test string: {test_string[:50]}...")

        except re.error as e:
            failed += 1
            print(f"  ✗ {pattern_name}: Invalid regex - {e}")

    return passed, failed


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    # Run config tests
    config_passed, config_failed = test_pattern_matching(verbose)

    # Run specific pattern tests
    pattern_passed, pattern_failed = test_specific_patterns(verbose)

    # Summary
    total_passed = config_passed + pattern_passed
    total_failed = config_failed + pattern_failed

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Config file tests: {config_passed} passed, {config_failed} failed")
    print(f"  Pattern tests: {pattern_passed} passed, {pattern_failed} failed")
    print(f"  Total: {total_passed} passed, {total_failed} failed")
    print("=" * 70)

    if total_failed == 0:
        print("\n✓ All security pattern tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total_failed} test(s) failed")
        sys.exit(1)


if __name__ == '__main__':
    main()

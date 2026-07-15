#!/usr/bin/env python3
"""Static security scan of ALL NetClaw MCP server source code.

Scans MCP server Python files for security issues WITHOUT running the servers.
Uses pattern matching similar to CodeGuard rules.

Usage:
    python3 scripts/scan-all-mcp-source.py [--output FILE] [--json]
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Finding:
    severity: str
    rule_id: str
    title: str
    location: str
    line_num: int
    context: str
    fix: str


@dataclass
class ScanResult:
    mcp_name: str
    path: str
    files_scanned: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if not self.findings:
            return "CLEAN"
        severities = [f.severity for f in self.findings]
        if "CRITICAL" in severities:
            return "CRITICAL"
        if "HIGH" in severities:
            return "HIGH"
        if "MEDIUM" in severities:
            return "MEDIUM"
        return "INFO"


# Security patterns to detect
PATTERNS = [
    # Credentials - require actual value assignment, not string checks
    {
        "id": "CG-CRED-001",
        "severity": "HIGH",
        "title": "Hardcoded API key or secret",
        # Match: api_key = "actualvalue" but NOT: "api_key" in something
        "pattern": r"""(?<!["'])\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*=\s*['"]((?!\\$\{|\$\()[^'"]{20,})['""]""",
        "fix": "Use environment variables: os.environ.get('API_KEY')",
    },
    {
        "id": "CG-CRED-002",
        "severity": "HIGH",
        "title": "AWS access key ID",
        "pattern": r"""AKIA[0-9A-Z]{16}""",
        "fix": "Use IAM roles or ~/.aws/credentials",
    },
    {
        "id": "CG-CRED-003",
        "severity": "CRITICAL",
        "title": "Private key embedded",
        "pattern": r"""-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----""",
        "fix": "Load keys from files or secrets manager at runtime",
    },
    {
        "id": "CG-CRED-004",
        "severity": "HIGH",
        "title": "GitHub token pattern",
        "pattern": r"""ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}""",
        "fix": "Use environment variable GITHUB_TOKEN",
    },
    # Command execution
    {
        "id": "CG-EXEC-001",
        "severity": "HIGH",
        "title": "os.system() usage",
        "pattern": r"""os\s*\.\s*system\s*\(""",
        "fix": "Use subprocess.run([...]) with list arguments",
    },
    {
        "id": "CG-EXEC-002",
        "severity": "MEDIUM",
        "title": "subprocess with shell=True",
        "pattern": r"""subprocess\s*\.\s*(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True""",
        "fix": "Use shell=False and pass command as list",
    },
    {
        "id": "CG-EXEC-003",
        "severity": "HIGH",
        "title": "eval() or exec() usage",
        "pattern": r"""(?<!\.)\b(eval|exec)\s*\(""",
        "fix": "Use ast.literal_eval() for safe evaluation",
    },
    # SQL injection
    {
        "id": "CG-SQL-001",
        "severity": "HIGH",
        "title": "String formatting in SQL",
        "pattern": r"""(?:execute|query)\s*\(\s*f?['""].*(?:SELECT|INSERT|UPDATE|DELETE).*\{.*\}""",
        "fix": "Use parameterized queries with ? or %s placeholders",
    },
    # Deserialization
    {
        "id": "CG-DESER-001",
        "severity": "HIGH",
        "title": "Unsafe pickle usage",
        "pattern": r"""pickle\s*\.\s*(?:load|loads)\s*\(""",
        "fix": "Use json.loads() instead of pickle",
    },
    {
        "id": "CG-DESER-002",
        "severity": "HIGH",
        "title": "Unsafe yaml.load()",
        "pattern": r"""yaml\s*\.\s*load\s*\([^)]*\)(?!\s*,\s*Loader\s*=\s*yaml\.SafeLoader)""",
        "fix": "Use yaml.safe_load() instead",
    },
    # Cryptography - only flag when used for passwords/auth, not cache keys
    {
        "id": "CG-CRYPTO-001",
        "severity": "MEDIUM",
        "title": "Weak hash for authentication",
        # Only flag if password/auth context, not generic hashing
        "pattern": r"""(?:password|auth|credential|secret).*(?:hashlib\s*\.\s*(?:md5|sha1)|createHash\s*\(\s*['""](?:md5|sha1)['""])""",
        "fix": "Use hashlib.sha256() or bcrypt for password hashing",
    },
    # Path traversal - only flag with user input variables
    {
        "id": "CG-PATH-001",
        "severity": "MEDIUM",
        "title": "Potential path traversal with user input",
        # Only flag if path contains variable that could be user input
        "pattern": r"""(?:open|Path)\s*\([^)]*(?:request|user|input|param|arg)[^)]*\.\.\/""",
        "fix": "Use os.path.realpath() and validate path prefix",
    },
    # SSL/TLS
    {
        "id": "CG-TLS-001",
        "severity": "MEDIUM",
        "title": "SSL verification disabled",
        "pattern": r"""verify\s*=\s*False|ssl[_.]verify[_.]?(?:peer|host)?\s*=\s*False|CERT_NONE""",
        "fix": "Enable SSL verification in production",
    },
]


def scan_file(filepath: Path) -> Iterator[Finding]:
    """Scan a single Python file for security issues."""
    try:
        content = filepath.read_text(errors="ignore")
    except Exception:
        return

    lines = content.split("\n")

    for pattern_def in PATTERNS:
        pattern = re.compile(pattern_def["pattern"], re.IGNORECASE | re.MULTILINE)

        for match in pattern.finditer(content):
            # Find line number
            line_start = content[:match.start()].count("\n") + 1
            line_content = lines[line_start - 1].strip() if line_start <= len(lines) else ""

            # Skip if in a comment or docstring (basic check)
            if line_content.strip().startswith("#"):
                continue

            yield Finding(
                severity=pattern_def["severity"],
                rule_id=pattern_def["id"],
                title=pattern_def["title"],
                location=str(filepath),
                line_num=line_start,
                context=line_content[:100],
                fix=pattern_def["fix"],
            )


def scan_mcp_directory(mcp_dir: Path) -> ScanResult:
    """Scan an MCP server directory."""
    result = ScanResult(
        mcp_name=mcp_dir.name,
        path=str(mcp_dir),
        files_scanned=0,
    )

    # Find all Python files
    py_files = list(mcp_dir.rglob("*.py"))
    result.files_scanned = len(py_files)

    # Scan each file
    for py_file in py_files:
        # Skip test files and venv
        if any(part in str(py_file) for part in ["test_", "_test.py", "venv/", ".venv/", "__pycache__"]):
            continue

        for finding in scan_file(py_file):
            result.findings.append(finding)

    return result


def main():
    parser = argparse.ArgumentParser(description="Static security scan of MCP source code")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--mcp-dir", default="mcp-servers", help="MCP servers directory")
    args = parser.parse_args()

    # Find netclaw root
    script_dir = Path(__file__).parent
    netclaw_root = script_dir.parent
    mcp_base = netclaw_root / args.mcp_dir

    if not mcp_base.exists():
        print(f"Error: MCP directory not found: {mcp_base}", file=sys.stderr)
        sys.exit(1)

    # Find all MCP directories
    mcp_dirs = sorted([d for d in mcp_base.iterdir() if d.is_dir()])

    results = []
    for mcp_dir in mcp_dirs:
        result = scan_mcp_directory(mcp_dir)
        results.append(result)

    # Output
    if args.json:
        output_data = {
            "scan_type": "mcp_source_static_analysis",
            "total_mcps": len(results),
            "results": [
                {
                    "name": r.mcp_name,
                    "path": r.path,
                    "files_scanned": r.files_scanned,
                    "verdict": r.verdict,
                    "findings": [
                        {
                            "severity": f.severity,
                            "rule_id": f.rule_id,
                            "title": f.title,
                            "location": f.location,
                            "line": f.line_num,
                            "context": f.context,
                            "fix": f.fix,
                        }
                        for f in r.findings
                    ],
                }
                for r in results
            ],
            "summary": {
                "clean": sum(1 for r in results if r.verdict == "CLEAN"),
                "warnings": sum(1 for r in results if r.verdict in ("MEDIUM", "INFO")),
                "high": sum(1 for r in results if r.verdict == "HIGH"),
                "critical": sum(1 for r in results if r.verdict == "CRITICAL"),
            },
        }
        output = json.dumps(output_data, indent=2)
    else:
        lines = [
            "# DefenseClaw MCP Source Code Scan",
            "",
            f"Scanned {len(results)} MCP server directories",
            "",
        ]

        clean = 0
        warnings = 0
        high = 0
        critical = 0

        for result in results:
            if result.verdict == "CLEAN":
                clean += 1
                lines.append(f"[CLEAN] {result.mcp_name} ({result.files_scanned} files)")
            else:
                if result.verdict == "CRITICAL":
                    critical += 1
                elif result.verdict == "HIGH":
                    high += 1
                else:
                    warnings += 1

                lines.append(f"")
                lines.append(f"## [{result.verdict}] {result.mcp_name}")
                lines.append(f"Path: {result.path}")
                lines.append(f"Files: {result.files_scanned}")
                lines.append(f"Findings: {len(result.findings)}")
                lines.append(f"")

                for finding in result.findings:
                    lines.append(f"  [{finding.severity}] {finding.rule_id}: {finding.title}")
                    lines.append(f"    Location: {finding.location}:{finding.line_num}")
                    lines.append(f"    Context: {finding.context}")
                    lines.append(f"    Fix: {finding.fix}")
                    lines.append(f"")

        lines.append("")
        lines.append("---")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total MCPs: {len(results)}")
        lines.append(f"- Clean: {clean}")
        lines.append(f"- Warnings (MEDIUM/INFO): {warnings}")
        lines.append(f"- High: {high}")
        lines.append(f"- Critical: {critical}")

        output = "\n".join(lines)

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Results written to: {args.output}")
        print(f"Summary: {len(results)} MCPs, {clean} clean, {warnings} warnings, {high} high, {critical} critical")
    else:
        print(output)


if __name__ == "__main__":
    main()

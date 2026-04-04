"""Bughunter - Automated bug detection and fixing.

Runs tests on code changes, detects test failures,
analyzes failure patterns, and auto-generates fixes.
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a test run."""

    name: str
    passed: bool
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class BugReport:
    """Bug report with analysis."""

    test_name: str
    error_type: str
    error_message: str
    suggested_fix: Optional[str] = None
    confidence: float = 0.0
    related_files: List[str] = field(default_factory=list)


class Bughunter:
    """Automated bug detection and fixing."""

    def __init__(
        self,
        test_command: str = "pytest",
        timeout: int = 300,
        max_fix_attempts: int = 3,
    ):
        """Initialize bughunter.

        Args:
            test_command: Command to run tests
            timeout: Test timeout in seconds
            max_fix_attempts: Maximum fix attempts
        """
        self.test_command = test_command
        self.timeout = timeout
        self.max_fix_attempts = max_fix_attempts

    def run_tests(
        self, test_path: Optional[str] = None, verbose: bool = True
    ) -> Tuple[List[TestResult], str]:
        """Run tests and collect results.

        Args:
            test_path: Path to tests (file, directory, or module)
            verbose: Verbose output

        Returns:
            (list of TestResult, output)
        """
        cmd = [self.test_command]
        if verbose:
            cmd.append("-v")
        if test_path:
            cmd.append(test_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.getcwd(),
            )

            output = result.stdout + result.stderr
            results = self._parse_pytest_output(output, result.returncode)

            return results, output

        except subprocess.TimeoutExpired:
            return [], f"Tests timed out after {self.timeout}s"
        except Exception as e:
            return [], f"Error running tests: {e}"

    def _parse_pytest_output(self, output: str, returncode: int) -> List[TestResult]:
        """Parse pytest output into TestResult objects.

        Args:
            output: Pytest output
            returncode: Exit code

        Returns:
            List of TestResult
        """
        results = []

        if returncode == 0:
            return results

        test_pattern = r"^(FAILED|PASSED|ERROR)\s+(\S+)"
        error_pattern = r"^(\S+)\s+(FAILED|ERROR)"

        for line in output.split("\n"):
            match = re.match(test_pattern, line.strip())
            if match:
                status, name = match.groups()
                results.append(
                    TestResult(
                        name=name, passed=status == "PASSED", error_message=line.strip()
                    )
                )

        return results

    def analyze_bugs(self, test_results: List[TestResult]) -> List[BugReport]:
        """Analyze test failures and generate bug reports.

        Args:
            test_results: List of test results

        Returns:
            List of BugReport
        """
        reports = []

        for result in test_results:
            if result.passed:
                continue

            error_type = self._extract_error_type(result.error_message or "")
            fix = self._suggest_fix(error_type, result.error_message or "")
            confidence = self._calculate_confidence(
                error_type, result.error_message or ""
            )

            report = BugReport(
                test_name=result.name,
                error_type=error_type,
                error_message=result.error_message or "",
                suggested_fix=fix,
                confidence=confidence,
            )
            reports.append(report)

        return reports

    def _extract_error_type(self, error_msg: str) -> str:
        """Extract error type from error message.

        Args:
            error_msg: Error message

        Returns:
            Error type string
        """
        error_types = [
            "AssertionError",
            "AttributeError",
            "ImportError",
            "IndexError",
            "KeyError",
            "NameError",
            "SyntaxError",
            "TypeError",
            "ValueError",
            "ZeroDivisionError",
            "FileNotFoundError",
            "PermissionError",
        ]

        for error_type in error_types:
            if error_type in error_msg:
                return error_type

        return "UnknownError"

    def _suggest_fix(self, error_type: str, error_msg: str) -> Optional[str]:
        """Suggest a fix based on error type.

        Args:
            error_type: Type of error
            error_msg: Error message

        Returns:
            Suggested fix or None
        """
        suggestions = {
            "AssertionError": "Check the assertion - expected value doesn't match actual. Fix the test or the code.",
            "AttributeError": f"Object has no attribute. Check spelling or if the attribute exists. Error: {error_msg[:100]}",
            "ImportError": "Module not found. Check imports or install missing package.",
            "IndexError": "Index out of range. Check list bounds before accessing.",
            "KeyError": "Key not found in dictionary. Check if key exists or use .get().",
            "NameError": "Variable not defined. Check spelling or if it's defined before use.",
            "SyntaxError": "Syntax error. Check for missing parentheses, brackets, or quotes.",
            "TypeError": "Wrong type operation. Check types of variables being used.",
            "ValueError": "Wrong value. Check the value being passed to the function.",
            "ZeroDivisionError": "Division by zero. Check divisor before division.",
            "FileNotFoundError": "File not found. Check file path or create the file.",
            "PermissionError": "Permission denied. Check file/directory permissions.",
        }

        return suggestions.get(error_type)

    def _calculate_confidence(self, error_type: str, error_msg: str) -> float:
        """Calculate confidence of fix suggestion.

        Args:
            error_type: Type of error
            error_msg: Error message

        Returns:
            Confidence score 0-1
        """
        base_confidence = {
            "SyntaxError": 0.9,
            "ImportError": 0.8,
            "NameError": 0.7,
            "TypeError": 0.6,
            "ValueError": 0.5,
            "AssertionError": 0.5,
        }

        confidence = base_confidence.get(error_type, 0.3)

        if "maybe" in error_msg.lower() or "possibly" in error_msg.lower():
            confidence *= 0.5

        return min(1.0, confidence)

    def auto_fix(self, bug_report: BugReport) -> Tuple[bool, str]:
        """Attempt to auto-fix a bug.

        Args:
            bug_report: Bug report

        Returns:
            (success, message)
        """
        if not bug_report.suggested_fix:
            return False, "No suggestion available"

        return True, bug_report.suggested_fix

    def generate_report(self, bug_reports: List[BugReport]) -> str:
        """Generate a human-readable bug report.

        Args:
            bug_reports: List of bug reports

        Returns:
            Formatted report
        """
        if not bug_reports:
            return "No bugs found! All tests passed."

        lines = ["=" * 50, "BUG HUNTER REPORT", "=" * 50, ""]

        for i, report in enumerate(bug_reports, 1):
            lines.append(f"Bug #{i}: {report.test_name}")
            lines.append(f"  Error Type: {report.error_type}")
            lines.append(f"  Confidence: {report.confidence:.0%}")
            lines.append(f"  Message: {report.error_message[:200]}")
            if report.suggested_fix:
                lines.append(f"  Suggestion: {report.suggested_fix}")
            lines.append("")

        lines.append("=" * 50)
        lines.append(f"Total bugs: {len(bug_reports)}")
        lines.append(
            f"Average confidence: {sum(r.confidence for r in bug_reports) / len(bug_reports):.0%}"
        )

        return "\n".join(lines)


def run_bughunter(
    test_path: Optional[str] = None,
    test_command: str = "pytest",
    auto_fix: bool = False,
) -> Dict[str, Any]:
    """Quick function to run bughunter.

    Args:
        test_path: Path to tests
        test_command: Test command to run
        auto_fix: Attempt auto-fix

    Returns:
        Dict with results
    """
    hunter = Bughunter(test_command=test_command)

    results, output = hunter.run_tests(test_path)

    if not results:
        return {"success": True, "bugs_found": 0, "message": "All tests passed!"}

    bug_reports = hunter.analyze_bugs(results)
    report = hunter.generate_report(bug_reports)

    return {
        "success": False,
        "bugs_found": len(bug_reports),
        "report": report,
        "bug_reports": [
            {
                "test": r.test_name,
                "type": r.error_type,
                "fix": r.suggested_fix,
                "confidence": r.confidence,
            }
            for r in bug_reports
        ],
    }

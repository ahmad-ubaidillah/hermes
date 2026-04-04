"""Auto-install utility for missing Python packages.

Automatically detects and installs missing Python packages when
ImportError or ModuleNotFoundError is raised during code execution.
"""

import logging
import re
import subprocess
import sys
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


PACKAGE_NAME_PATTERN = re.compile(
    r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]|"
    r"ImportError: cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]|"
    r"ImportError: ['\"]([^'\"]+)['\"]|"
    r"Could not find module ['\"]([^'\"]+)['\"]"
)


def extract_package_from_error(error_output: str) -> Optional[str]:
    """Extract package name from error output.

    Args:
        error_output: The error message from failed execution

    Returns:
        Package name if found, None otherwise
    """
    match = PACKAGE_NAME_PATTERN.search(error_output)
    if match:
        for group in match.groups():
            if group and not group.startswith("."):
                return group
    return None


def install_package(package_name: str, timeout: int = 120) -> Tuple[bool, str]:
    """Install a Python package using pip.

    Args:
        package_name: Name of the package to install
        timeout: Timeout in seconds for the install command

    Returns:
        (success, message) tuple
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            logger.info(f"Successfully installed package: {package_name}")
            return True, f"Successfully installed {package_name}"
        else:
            error_msg = result.stderr or result.stdout
            logger.warning(f"Failed to install {package_name}: {error_msg}")
            return False, f"Failed to install {package_name}: {error_msg}"

    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout installing {package_name}")
        return False, f"Timeout installing {package_name}"
    except Exception as e:
        logger.warning(f"Error installing {package_name}: {e}")
        return False, f"Error installing {package_name}: {e}"


def handle_missing_package(
    error_output: str, auto_install: bool = True, timeout: int = 120
) -> Tuple[bool, str]:
    """Handle missing package error.

    Args:
        error_output: The error message from failed execution
        auto_install: Whether to automatically install missing packages
        timeout: Timeout in seconds for the install command

    Returns:
        (can_retry, message) tuple
        - can_retry: True if package was installed and execution can be retried
        - message: Status message
    """
    package_name = extract_package_from_error(error_output)

    if not package_name:
        return False, "No package name found in error"

    if not auto_install:
        return False, f"Missing package: {package_name} (auto-install disabled)"

    success, message = install_package(package_name, timeout)
    return success, message


def is_import_error(error_output: str) -> bool:
    """Check if error is import-related.

    Args:
        error_output: The error message

    Returns:
        True if error is import-related
    """
    import_errors = [
        "ModuleNotFoundError",
        "ImportError",
        "No module named",
        "cannot import name",
        "could not find module",
    ]

    error_lower = error_output.lower()
    return any(err.lower() in error_lower for err in import_errors)


def should_auto_install(error_output: str) -> bool:
    """Check if error should trigger auto-install.

    Args:
        error_output: The error message

    Returns:
        True if this looks like a missing package error
    """
    if not is_import_error(error_output):
        return False

    no_package_patterns = [
        r"ModuleNotFoundError: No module named",
        r"ImportError: cannot import name",
        r"ImportError: No module named",
    ]

    for pattern in no_package_patterns:
        if re.search(pattern, error_output):
            return True

    return False

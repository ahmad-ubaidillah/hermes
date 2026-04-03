"""Granular policy engine for tool execution control.

Provides fine-grained per-tool approval rules, command allowlist/denylist
patterns, file path restrictions, and network access controls.

This engine sits between the model's tool call request and actual tool
execution, evaluating each call against the configured policy before
allowing it to proceed.

Policy levels (evaluated in order, first match wins):
  1. ALWAYS_DENY  - Block immediately, no approval prompt
  2. ALWAYS_ALLOW - Skip approval, execute directly
  3. ASK          - Require user approval (default)

Configuration (config.yaml):
  security:
    policy_engine:
      enabled: true
      tool_policies:
        terminal: ask
        web_search: always_allow
        write_file: ask
      command_allowlist:
        - "ls"
        - "cat"
        - "git status"
      command_denylist:
        - "rm -rf /"
        - "mkfs"
      path_restrictions:
        deny_prefixes:
          - "/etc/"
          - "/root/"
          - "/boot/"
          - "/sys/"
          - "/proc/"
        allow_prefixes:
          - "/home/"
          - "/tmp/"
      network_restrictions:
        allowlist_domains: []        # empty = all allowed
        denylist_domains:
          - "malicious.example.com"
        block_private_ips: false
"""

import fnmatch
import ipaddress
import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    ALWAYS_ALLOW = "always_allow"
    ALWAYS_DENY = "always_deny"
    ASK = "ask"


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    action: PolicyAction
    reason: str = ""
    matched_rule: str = ""

    @property
    def allowed(self) -> bool:
        return self.action in (PolicyAction.ALWAYS_ALLOW, PolicyAction.ASK)


@dataclass
class PolicyConfig:
    """Configuration for the policy engine."""

    enabled: bool = True
    tool_policies: Dict[str, str] = field(default_factory=dict)
    command_allowlist: List[str] = field(default_factory=list)
    command_denylist: List[str] = field(default_factory=list)
    path_deny_prefixes: List[str] = field(default_factory=list)
    path_allow_prefixes: List[str] = field(default_factory=list)
    network_allowlist_domains: List[str] = field(default_factory=list)
    network_denylist_domains: List[str] = field(default_factory=list)
    block_private_ips: bool = False


class PolicyEngine:
    """Granular policy engine for tool execution control.

    Evaluates tool calls against configured policies to determine whether
    they should be allowed, denied, or require user approval.
    """

    _DEFAULT_PATH_DENY_PREFIXES = ["/etc/", "/root/", "/boot/", "/sys/", "/proc/"]
    _DEFAULT_PATH_ALLOW_PREFIXES = ["/home/", "/tmp/", "./", "~/"]

    def __init__(self, config: Optional[PolicyConfig] = None):
        self._config = config or PolicyConfig()
        self._compiled_command_allowlist: List[re.Pattern] = []
        self._compiled_command_denylist: List[re.Pattern] = []
        self._compile_patterns()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PolicyEngine":
        """Create a PolicyEngine from a config dictionary (e.g. from YAML)."""
        policy_cfg = config_dict.get("security", {}).get("policy_engine", {})
        if not policy_cfg:
            return cls()

        restrictions = policy_cfg.get("path_restrictions", {})
        network = policy_cfg.get("network_restrictions", {})

        cfg = PolicyConfig(
            enabled=policy_cfg.get("enabled", True),
            tool_policies=policy_cfg.get("tool_policies", {}),
            command_allowlist=policy_cfg.get("command_allowlist", []),
            command_denylist=policy_cfg.get("command_denylist", []),
            path_deny_prefixes=restrictions.get(
                "deny_prefixes", cls._DEFAULT_PATH_DENY_PREFIXES
            ),
            path_allow_prefixes=restrictions.get(
                "allow_prefixes", cls._DEFAULT_PATH_ALLOW_PREFIXES
            ),
            network_allowlist_domains=network.get("allowlist_domains", []),
            network_denylist_domains=network.get("denylist_domains", []),
            block_private_ips=network.get("block_private_ips", False),
        )
        return cls(cfg)

    @classmethod
    def from_config_path(cls, config_path: str) -> "PolicyEngine":
        """Load policy config from a YAML file."""
        try:
            import yaml

            with open(config_path) as f:
                config_dict = yaml.safe_load(f) or {}
            return cls.from_dict(config_dict)
        except FileNotFoundError:
            return cls()
        except Exception as e:
            logger.warning("Failed to load policy config from %s: %s", config_path, e)
            return cls()

    def update_config(self, config_dict: Dict[str, Any]) -> None:
        """Update engine configuration at runtime."""
        self._config = PolicyConfig(
            enabled=config_dict.get("enabled", self._config.enabled),
            tool_policies=config_dict.get("tool_policies", self._config.tool_policies),
            command_allowlist=config_dict.get(
                "command_allowlist", self._config.command_allowlist
            ),
            command_denylist=config_dict.get(
                "command_denylist", self._config.command_denylist
            ),
            path_deny_prefixes=config_dict.get(
                "path_deny_prefixes", self._config.path_deny_prefixes
            ),
            path_allow_prefixes=config_dict.get(
                "path_allow_prefixes", self._config.path_allow_prefixes
            ),
            network_allowlist_domains=config_dict.get(
                "network_allowlist_domains", self._config.network_allowlist_domains
            ),
            network_denylist_domains=config_dict.get(
                "network_denylist_domains", self._config.network_denylist_domains
            ),
            block_private_ips=config_dict.get(
                "block_private_ips", self._config.block_private_ips
            ),
        )
        self._compile_patterns()

    # ------------------------------------------------------------------
    # Pattern compilation
    # ------------------------------------------------------------------

    def _compile_patterns(self) -> None:
        """Pre-compile allowlist/denylist patterns for fast matching."""
        self._compiled_command_allowlist = [
            self._compile_pattern(p) for p in self._config.command_allowlist
        ]
        self._compiled_command_denylist = [
            self._compile_pattern(p) for p in self._config.command_denylist
        ]

    @staticmethod
    def _compile_pattern(pattern: str) -> re.Pattern:
        """Compile a pattern that supports both regex and glob syntax."""
        if any(c in pattern for c in ".*+?^${}()|[]\\"):
            return re.compile(pattern, re.IGNORECASE)
        return re.compile(fnmatch.translate(pattern), re.IGNORECASE)

    # ------------------------------------------------------------------
    # Main evaluation
    # ------------------------------------------------------------------

    def evaluate(self, tool_name: str, tool_args: Dict[str, Any]) -> PolicyDecision:
        """Evaluate a tool call against all policies.

        Args:
            tool_name: Name of the tool being called (e.g. "terminal", "write_file")
            tool_args: Arguments passed to the tool

        Returns:
            PolicyDecision with action, reason, and matched rule
        """
        if not self._config.enabled:
            return PolicyDecision(
                PolicyAction.ALWAYS_ALLOW, reason="Policy engine disabled"
            )

        # 1. Check per-tool policy
        tool_decision = self._check_tool_policy(tool_name)
        if tool_decision:
            return tool_decision

        # 2. Check command allowlist/denylist (for terminal/exec tools)
        cmd_decision = self._check_command_policy(tool_name, tool_args)
        if cmd_decision:
            return cmd_decision

        # 3. Check path restrictions
        path_decision = self._check_path_policy(tool_name, tool_args)
        if path_decision:
            return path_decision

        # 4. Check network restrictions
        net_decision = self._check_network_policy(tool_name, tool_args)
        if net_decision:
            return net_decision

        # Default: ask for approval
        return PolicyDecision(PolicyAction.ASK, reason="No matching policy rule")

    # ------------------------------------------------------------------
    # Policy checks
    # ------------------------------------------------------------------

    def _check_tool_policy(self, tool_name: str) -> Optional[PolicyDecision]:
        """Check per-tool policy (always_allow, always_deny, ask)."""
        policy = self._config.tool_policies.get(tool_name)
        if policy is None:
            return None

        try:
            action = PolicyAction(policy.lower())
        except ValueError:
            logger.warning(
                "Unknown policy action '%s' for tool '%s'", policy, tool_name
            )
            return None

        return PolicyDecision(
            action,
            reason=f"Tool policy: {tool_name} -> {policy}",
            matched_rule=f"tool_policies.{tool_name}",
        )

    def _check_command_policy(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Optional[PolicyDecision]:
        """Check command allowlist/denylist for terminal and execution tools."""
        if tool_name not in ("terminal", "execute_code", "exec"):
            return None

        command = self._extract_command(tool_args)
        if not command:
            return None

        # Denylist takes priority
        for pattern in self._compiled_command_denylist:
            if pattern.search(command):
                return PolicyDecision(
                    PolicyAction.ALWAYS_DENY,
                    reason=f"Command matches denylist pattern: {pattern.pattern}",
                    matched_rule=f"command_denylist:{pattern.pattern}",
                )

        # If allowlist is configured, command must match
        if self._compiled_command_allowlist:
            for pattern in self._compiled_command_allowlist:
                if pattern.search(command):
                    return PolicyDecision(
                        PolicyAction.ALWAYS_ALLOW,
                        reason=f"Command matches allowlist pattern: {pattern.pattern}",
                        matched_rule=f"command_allowlist:{pattern.pattern}",
                    )
            return PolicyDecision(
                PolicyAction.ALWAYS_DENY,
                reason=f"Command not in allowlist: {command}",
                matched_rule="command_allowlist",
            )

        return None

    def _check_path_policy(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Optional[PolicyDecision]:
        """Check file path restrictions for file operation tools."""
        file_tools = {
            "write_file",
            "read_file",
            "patch",
            "edit",
            "terminal",
            "execute_code",
        }
        if tool_name not in file_tools:
            return None

        paths = self._extract_paths(tool_name, tool_args)
        if not paths:
            return None

        deny_prefixes = (
            self._config.path_deny_prefixes or self._DEFAULT_PATH_DENY_PREFIXES
        )

        for path_str in paths:
            resolved = str(Path(path_str).expanduser().resolve())

            for prefix in deny_prefixes:
                prefix_resolved = str(Path(prefix).expanduser().resolve())
                if resolved.startswith(prefix_resolved):
                    return PolicyDecision(
                        PolicyAction.ALWAYS_DENY,
                        reason=f"Path '{path_str}' matches denied prefix '{prefix}'",
                        matched_rule=f"path_deny:{prefix}",
                    )

        # If allowlist is configured, all paths must match an allowed prefix
        allow_prefixes = self._config.path_allow_prefixes
        if allow_prefixes:
            for path_str in paths:
                resolved = str(Path(path_str).expanduser().resolve())
                if not any(
                    resolved.startswith(str(Path(p).expanduser().resolve()))
                    for p in allow_prefixes
                ):
                    return PolicyDecision(
                        PolicyAction.ALWAYS_DENY,
                        reason=f"Path '{path_str}' not in allowed prefixes",
                        matched_rule="path_allowlist",
                    )

        return None

    def _check_network_policy(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Optional[PolicyDecision]:
        """Check network access restrictions for web/browser tools."""
        network_tools = {
            "web_search",
            "web_fetch",
            "browser_navigate",
            "http_request",
            "curl",
        }
        if tool_name not in network_tools:
            return None

        urls = self._extract_urls(tool_name, tool_args)
        if not urls:
            return None

        # Check denylist
        for url_str in urls:
            domain = self._extract_domain(url_str)
            if not domain:
                continue

            for denied in self._config.network_denylist_domains:
                if domain == denied or domain.endswith("." + denied):
                    return PolicyDecision(
                        PolicyAction.ALWAYS_DENY,
                        reason=f"Domain '{domain}' is in network denylist",
                        matched_rule=f"network_denylist:{denied}",
                    )

        # Check allowlist (if configured, only allowlisted domains permitted)
        if self._config.network_allowlist_domains:
            for url_str in urls:
                domain = self._extract_domain(url_str)
                if not domain:
                    continue
                if not any(
                    domain == allowed or domain.endswith("." + allowed)
                    for allowed in self._config.network_allowlist_domains
                ):
                    return PolicyDecision(
                        PolicyAction.ALWAYS_DENY,
                        reason=f"Domain '{domain}' not in network allowlist",
                        matched_rule="network_allowlist",
                    )

        # Check private IP blocking
        if self._config.block_private_ips:
            for url_str in urls:
                domain = self._extract_domain(url_str)
                if domain and self._is_private_ip(domain):
                    return PolicyDecision(
                        PolicyAction.ALWAYS_DENY,
                        reason=f"Private IP access blocked: {domain}",
                        matched_rule="block_private_ips",
                    )

        return None

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_command(tool_args: Dict[str, Any]) -> Optional[str]:
        """Extract command string from tool arguments."""
        for key in ("command", "cmd", "code", "script", "code_to_execute"):
            val = tool_args.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None

    @staticmethod
    def _extract_paths(tool_name: str, tool_args: Dict[str, Any]) -> List[str]:
        """Extract file paths from tool arguments."""
        paths = []
        path_keys = (
            "path",
            "file_path",
            "filepath",
            "filename",
            "target",
            "destination",
            "dest",
            "output_path",
            "directory",
        )
        for key in path_keys:
            val = tool_args.get(key)
            if isinstance(val, str) and val.strip():
                paths.append(val.strip())

        # For terminal commands, extract paths from the command string
        if tool_name == "terminal":
            cmd = tool_args.get("command", "")
            if isinstance(cmd, str):
                # Match quoted paths and unquoted path-like arguments
                paths.extend(re.findall(r'"([^"]*\/[^"]*)"', cmd))
                paths.extend(re.findall(r"'([^']*\/[^']*)'", cmd))

        return paths

    @staticmethod
    def _extract_urls(tool_name: str, tool_args: Dict[str, Any]) -> List[str]:
        """Extract URLs from tool arguments."""
        urls = []
        url_keys = ("url", "urls", "target_url", "endpoint", "address")
        for key in url_keys:
            val = tool_args.get(key)
            if isinstance(val, str) and val.strip():
                urls.append(val.strip())
            elif isinstance(val, list):
                urls.extend(str(u) for u in val if isinstance(u, str) and u.strip())

        # For terminal commands, extract URLs
        if tool_name == "terminal":
            cmd = tool_args.get("command", "")
            if isinstance(cmd, str):
                urls.extend(re.findall(r'https?://[^\s"\']+', cmd))

        return urls

    @staticmethod
    def _extract_domain(url: str) -> Optional[str]:
        """Extract domain from a URL string."""
        try:
            parsed = urlparse(url)
            return parsed.hostname
        except Exception:
            return None

    @staticmethod
    def _is_private_ip(host: str) -> bool:
        """Check if a hostname resolves to a private IP address."""
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            # Not an IP address - could be a hostname like localhost
            private_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
            return host.lower() in private_hosts

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def set_tool_policy(self, tool_name: str, action: str) -> None:
        """Set policy for a specific tool."""
        self._config.tool_policies[tool_name] = action

    def add_command_to_denylist(self, pattern: str) -> None:
        """Add a command pattern to the denylist."""
        self._config.command_denylist.append(pattern)
        self._compile_patterns()

    def add_command_to_allowlist(self, pattern: str) -> None:
        """Add a command pattern to the allowlist."""
        self._config.command_allowlist.append(pattern)
        self._compile_patterns()

    def add_path_restriction(self, prefix: str, deny: bool = True) -> None:
        """Add a path prefix restriction."""
        if deny:
            if prefix not in self._config.path_deny_prefixes:
                self._config.path_deny_prefixes.append(prefix)
        else:
            if prefix not in self._config.path_allow_prefixes:
                self._config.path_allow_prefixes.append(prefix)

    def add_domain_to_denylist(self, domain: str) -> None:
        """Add a domain to the network denylist."""
        if domain not in self._config.network_denylist_domains:
            self._config.network_denylist_domains.append(domain)

    def add_domain_to_allowlist(self, domain: str) -> None:
        """Add a domain to the network allowlist."""
        if domain not in self._config.network_allowlist_domains:
            self._config.network_allowlist_domains.append(domain)

    def get_config_summary(self) -> Dict[str, Any]:
        """Return a summary of the current policy configuration."""
        return {
            "enabled": self._config.enabled,
            "tool_policies": dict(self._config.tool_policies),
            "command_allowlist_count": len(self._config.command_allowlist),
            "command_denylist_count": len(self._config.command_denylist),
            "path_deny_prefixes": list(self._config.path_deny_prefixes),
            "path_allow_prefixes": list(self._config.path_allow_prefixes),
            "network_allowlist_domains": list(self._config.network_allowlist_domains),
            "network_denylist_domains": list(self._config.network_denylist_domains),
            "block_private_ips": self._config.block_private_ips,
        }

"""Trajectory compression for Aizen conversation histories."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.aizen_constants import OPENROUTER_BASE_URL


# ---------------------------------------------------------------------------
# CompressionConfig
# ---------------------------------------------------------------------------


@dataclass
class CompressionConfig:
    tokenizer_name: str = "gpt2"
    trust_remote_code: bool = False
    target_max_tokens: int = 15250
    summary_target_tokens: int = 750
    protect_first_system: bool = True
    protect_first_human: bool = True
    protect_last_n_turns: int = 4
    summarization_model: str = "anthropic/claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_retries: int = 3
    add_summary_notice: bool = True
    output_suffix: str = "_short"
    num_workers: int = 4
    max_concurrent_requests: int = 50
    skip_under_target: bool = True
    save_over_limit: bool = False
    metrics_enabled: bool = True
    metrics_per_trajectory: bool = False
    metrics_output_file: str = "compression_metrics.json"
    base_url: str = OPENROUTER_BASE_URL
    api_key_env: str = "OPENROUTER_API_KEY"

    @classmethod
    def from_yaml(cls, path: str) -> "CompressionConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        tokenizer = data.get("tokenizer", {})
        if tokenizer:
            config.tokenizer_name = tokenizer.get("name", config.tokenizer_name)
            config.trust_remote_code = tokenizer.get(
                "trust_remote_code", config.trust_remote_code
            )

        compression = data.get("compression", {})
        if compression:
            config.target_max_tokens = compression.get(
                "target_max_tokens", config.target_max_tokens
            )
            config.summary_target_tokens = compression.get(
                "summary_target_tokens", config.summary_target_tokens
            )

        protected = data.get("protected_turns", {})
        if protected:
            config.protect_first_system = protected.get(
                "first_system", config.protect_first_system
            )
            config.protect_first_human = protected.get(
                "first_human", config.protect_first_human
            )
            config.protect_last_n_turns = protected.get(
                "last_n_turns", config.protect_last_n_turns
            )

        summarization = data.get("summarization", {})
        if summarization:
            config.summarization_model = summarization.get(
                "model", config.summarization_model
            )
            config.temperature = summarization.get("temperature", config.temperature)
            config.max_retries = summarization.get("max_retries", config.max_retries)
            config.base_url = summarization.get("base_url") or config.base_url

        output = data.get("output", {})
        if output:
            config.add_summary_notice = output.get(
                "add_summary_notice", config.add_summary_notice
            )
            config.output_suffix = output.get("output_suffix", config.output_suffix)

        processing = data.get("processing", {})
        if processing:
            config.num_workers = processing.get("num_workers", config.num_workers)
            config.max_concurrent_requests = processing.get(
                "max_concurrent_requests", config.max_concurrent_requests
            )
            config.skip_under_target = processing.get(
                "skip_under_target", config.skip_under_target
            )
            config.save_over_limit = processing.get(
                "save_over_limit", config.save_over_limit
            )

        metrics = data.get("metrics", {})
        if metrics:
            config.metrics_enabled = metrics.get("enabled", config.metrics_enabled)
            config.metrics_per_trajectory = metrics.get(
                "per_trajectory", config.metrics_per_trajectory
            )
            config.metrics_output_file = metrics.get(
                "output_file", config.metrics_output_file
            )

        return config


# ---------------------------------------------------------------------------
# TrajectoryMetrics
# ---------------------------------------------------------------------------


@dataclass
class TrajectoryMetrics:
    original_tokens: int = 0
    compressed_tokens: int = 0
    tokens_saved: int = 0
    compression_ratio: float = 1.0
    original_turns: int = 0
    compressed_turns: int = 0
    turns_removed: int = 0
    was_compressed: bool = False
    skipped_under_target: bool = False
    still_over_limit: bool = False
    summarization_success: bool = False
    summarization_retries: int = 0
    compression_region: dict = field(
        default_factory=lambda: {"start_idx": -1, "end_idx": -1}
    )

    def to_dict(self) -> dict:
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": self.compression_ratio,
            "original_turns": self.original_turns,
            "compressed_turns": self.compressed_turns,
            "turns_removed": self.turns_removed,
            "was_compressed": self.was_compressed,
            "skipped_under_target": self.skipped_under_target,
            "still_over_limit": self.still_over_limit,
            "summarization_success": self.summarization_success,
            "summarization_retries": self.summarization_retries,
            "compression_region": self.compression_region,
        }


# ---------------------------------------------------------------------------
# AggregateMetrics
# ---------------------------------------------------------------------------


@dataclass
class AggregateMetrics:
    total_trajectories: int = 0
    trajectories_compressed: int = 0
    trajectories_skipped_under_target: int = 0
    trajectories_still_over_limit: int = 0
    total_tokens_saved: int = 0
    compression_ratios: list = field(default_factory=list)
    summarization_attempts: int = 0
    summarization_successes: int = 0
    total_original_tokens: int = 0
    total_compressed_tokens: int = 0

    def add_trajectory_metrics(self, m: TrajectoryMetrics) -> None:
        self.total_trajectories += 1
        self.total_original_tokens += m.original_tokens
        self.total_compressed_tokens += m.compressed_tokens
        if m.was_compressed:
            self.trajectories_compressed += 1
            self.total_tokens_saved += m.tokens_saved
            self.compression_ratios.append(m.compression_ratio)
        if m.skipped_under_target:
            self.trajectories_skipped_under_target += 1
        if m.still_over_limit:
            self.trajectories_still_over_limit += 1
        if m.summarization_success:
            self.summarization_successes += 1
        if m.was_compressed or m.summarization_retries > 0:
            self.summarization_attempts += 1

    def to_dict(self) -> dict:
        n = len(self.compression_ratios)
        avg_ratio = sum(self.compression_ratios) / n if n else 1.0
        avg_saved = self.total_tokens_saved / n if n else 0
        total_saved = self.total_tokens_saved
        overall_ratio = (
            (self.total_original_tokens - self.total_compressed_tokens)
            / self.total_original_tokens
            if self.total_original_tokens
            else 0.0
        )
        success_rate = (
            self.summarization_successes / self.summarization_attempts
            if self.summarization_attempts
            else 1.0
        )
        return {
            "summary": {
                "total_trajectories": self.total_trajectories,
                "trajectories_compressed": self.trajectories_compressed,
                "trajectories_skipped_under_target": self.trajectories_skipped_under_target,
                "trajectories_still_over_limit": self.trajectories_still_over_limit,
            },
            "tokens": {
                "total_original": self.total_original_tokens,
                "total_compressed": self.total_compressed_tokens,
                "total_saved": total_saved,
                "overall_compression_ratio": overall_ratio,
            },
            "averages": {
                "avg_compression_ratio": avg_ratio,
                "avg_tokens_saved_per_compressed": avg_saved,
            },
            "summarization": {
                "attempts": self.summarization_attempts,
                "successes": self.summarization_successes,
                "success_rate": success_rate,
            },
        }


# ---------------------------------------------------------------------------
# TrajectoryCompressor
# ---------------------------------------------------------------------------


class TrajectoryCompressor:
    def __init__(self, config: CompressionConfig) -> None:
        self.config = config
        self.async_client = None
        self._async_client_api_key = None
        self._use_call_llm = False
        self.tokenizer = None
        self.client = None
        self._init_tokenizer()
        self._init_summarizer()

    def _init_tokenizer(self) -> None:
        try:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.tokenizer_name,
                trust_remote_code=self.config.trust_remote_code,
            )
        except Exception:
            self.tokenizer = None

    def _init_summarizer(self) -> None:
        try:
            from openai import OpenAI

            api_key = os.environ.get(self.config.api_key_env, "")
            self.client = OpenAI(api_key=api_key, base_url=self.config.base_url)
        except Exception:
            self.client = None

    def _get_async_client(self):
        from openai import AsyncOpenAI
        if self._async_client_api_key:
            api_key = self._async_client_api_key
        else:
            api_key_env = str(getattr(self.config, "api_key_env", "OPENROUTER_API_KEY"))
            api_key = os.environ.get(api_key_env, "")
            self._async_client_api_key = api_key
        base_url = str(getattr(self.config, "base_url", OPENROUTER_BASE_URL))
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self.async_client

    def _detect_provider(self) -> str:
        url = self.config.base_url or ""
        if "openrouter" in url.lower():
            return "openrouter"
        if "anthropic" in url.lower():
            return "anthropic"
        if "openai" in url.lower():
            return "openai"
        return ""

    def _find_protected_indices(self, trajectory: list) -> tuple:
        protected = set()
        n = len(trajectory)

        # Protect first occurrence of each role
        seen_roles = set()
        for i, turn in enumerate(trajectory):
            role = turn.get("from", "")
            if role not in seen_roles:
                if role == "system" and self.config.protect_first_system:
                    protected.add(i)
                elif role == "human" and self.config.protect_first_human:
                    protected.add(i)
                elif role in ("gpt", "tool"):
                    protected.add(i)
                seen_roles.add(role)

        # Protect last N turns
        last_n = self.config.protect_last_n_turns
        if last_n > 0:
            for i in range(max(0, n - last_n), n):
                protected.add(i)

        # Find compressible region (between head protection and tail protection)
        head_end = 0
        for i in range(n):
            if i in protected:
                head_end = i + 1
            else:
                break

        tail_start = n
        for i in range(n - 1, -1, -1):
            if i in protected:
                tail_start = i
            else:
                break

        return protected, head_end, tail_start

    def _extract_turn_content_for_summary(
        self, trajectory: list, start: int, end: int
    ) -> str:
        if start >= end:
            return ""
        parts = []
        max_chars = 4000
        total = 0
        for i in range(start, end):
            turn = trajectory[i]
            role = turn.get("from", "unknown").upper()
            content = str(turn.get("value", ""))
            line = f"[Turn {i} - {role}] {content}"
            if total + len(line) > max_chars:
                remaining = max_chars - total
                parts.append(line[:remaining] + "...[truncated]...")
                break
            parts.append(line)
            total += len(line)
        return "\n".join(parts)

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4

    def count_trajectory_tokens(self, trajectory: list) -> int:
        total = 0
        for turn in trajectory:
            total += self.count_tokens(str(turn.get("value", "")))
        return total

    def count_turn_tokens(self, trajectory: list) -> list:
        return [self.count_tokens(str(turn.get("value", ""))) for turn in trajectory]

    def _generate_summary(self, content: str, metrics: TrajectoryMetrics) -> str:
        if not self.client:
            return "[CONTEXT SUMMARY]:"
        try:
            resp = self.client.chat.completions.create(
                model=self.config.summarization_model,
                messages=[{"role": "user", "content": f"Summarize: {content}"}],
                temperature=self.config.temperature,
                max_tokens=self.config.summary_target_tokens,
            )
            summary = resp.choices[0].message.content
            if summary is None:
                return "[CONTEXT SUMMARY]:"
            return summary
        except Exception:
            return "[CONTEXT SUMMARY]:"

    async def _generate_summary_async(
        self, content: str, metrics: TrajectoryMetrics
    ) -> str:
        client = self._get_async_client()
        if not client:
            return "[CONTEXT SUMMARY]:"
        try:
            resp = await client.chat.completions.create(
                model=self.config.summarization_model,
                messages=[{"role": "user", "content": f"Summarize: {content}"}],
                temperature=self.config.temperature,
                max_tokens=self.config.summary_target_tokens,
            )
            summary = resp.choices[0].message.content
            if summary is None:
                return "[CONTEXT SUMMARY]:"
            return summary
        except Exception:
            return "[CONTEXT SUMMARY]:"

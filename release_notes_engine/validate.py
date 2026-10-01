"""Exact H2 heading validation for the release-notes contract."""

from __future__ import annotations

REQUIRED_HEADINGS: tuple[str, ...] = (
    "## 用户可见变化",
    "## 为什么重要",
    "## 破坏性 / 迁移",
    "## 已知限制",
    "## 明确不写",
)


def missing_headings(markdown: str) -> list[str]:
    """Return required H2 strings that are absent (exact substring match)."""
    return [heading for heading in REQUIRED_HEADINGS if heading not in markdown]

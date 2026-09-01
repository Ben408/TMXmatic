"""Minimal semver helpers — no external packaging dependency."""

from __future__ import annotations


def _parse_version(value: str) -> tuple[int, int, int]:
    """Parse ``major.minor.patch``; non-numeric suffixes are ignored."""
    parts = (value or "0.0.0").strip().split(".")
    nums: list[int] = []
    for part in parts[:3]:
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        nums.append(int(digits or "0"))
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def version_in_range(
    core_version: str,
    min_version: str | None,
    max_version: str | None,
) -> bool:
    """True when ``core_version`` satisfies optional inclusive bounds."""
    current = _parse_version(core_version)
    if min_version:
        if current < _parse_version(min_version):
            return False
    if max_version:
        if current > _parse_version(max_version):
            return False
    return True

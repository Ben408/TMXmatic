"""Unit tests for semver compatibility checks."""

from ldw_core.semver import version_in_range


def test_version_in_range_within_bounds():
    assert version_in_range("1.3.0", "1.3.0", "1.4.0") is True
    assert version_in_range("1.3.5", "1.3.0", "1.4.0") is True


def test_version_in_range_below_min():
    assert version_in_range("1.2.9", "1.3.0", "1.4.0") is False


def test_version_in_range_above_max():
    assert version_in_range("1.5.0", "1.3.0", "1.4.0") is False


def test_version_in_range_open_max():
    assert version_in_range("2.0.0", "1.3.0", None) is True

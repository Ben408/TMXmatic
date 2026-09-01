"""Unit tests for modules.json registry loading."""

from __future__ import annotations

import json

from ldw_core.module_registry import ModuleRegistry


def test_missing_registry_returns_empty_modules(app_path):
    registry = ModuleRegistry(app_path)
    payload = registry.list_for_api("1.3.0")
    assert payload["schema_version"] == 1
    assert payload["modules"] == []
    assert payload["ldw_core_version"] == "1.3.0"


def test_register_and_list_module(app_path):
    registry = ModuleRegistry(app_path)
    registry.register_module(
        {
            "id": "ldw-llm-quality",
            "version": "0.1.0",
            "ldw_min": "1.3.0",
            "ldw_max": "1.4.0",
            "gpu_required": True,
            "installed_at": "2026-08-31T00:00:00Z",
            "manifest_path": "modules/ldw-llm-quality/manifest.json",
        }
    )
    payload = registry.list_for_api("1.3.0")
    assert len(payload["modules"]) == 1
    row = payload["modules"][0]
    assert row["id"] == "ldw-llm-quality"
    assert row["compatible"] is True
    assert row["gpu_required"] is True


def test_incompatible_module_flag(app_path):
    registry = ModuleRegistry(app_path)
    registry.register_module(
        {
            "id": "future-module",
            "version": "9.0.0",
            "ldw_min": "2.0.0",
            "manifest_path": "modules/future/manifest.json",
        }
    )
    payload = registry.list_for_api("1.3.0")
    assert payload["modules"][0]["compatible"] is False


def test_validate_entry_requires_id(app_path):
    registry = ModuleRegistry(app_path)
    try:
        registry.validate_entry({"version": "0.1.0"})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "id" in str(exc)

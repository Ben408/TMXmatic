"""Unit tests for Okapi operation registry."""

from ldw_core.okapi.operation_registry import OkapiOperationRegistry


def test_registry_loads_convert_operation(app_path):
    # Copy minimal registry when app_path is tmp (tests use LDW root via fixture override).
    import shutil
    import os

    src = os.path.join(os.path.dirname(__file__), "..", "config", "okapi_operations.yml")
    dest_dir = os.path.join(app_path, "config")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, "okapi_operations.yml"))

    registry = OkapiOperationRegistry(app_path)
    op = registry.get("convert")
    assert op is not None
    assert "docx" in op.input_formats
    assert registry.supports_input_extension("convert", "docx") is True
    assert registry.supports_input_extension("convert", "exe") is False


def test_registry_list_for_api(app_path):
    import shutil
    import os

    src = os.path.join(os.path.dirname(__file__), "..", "config", "okapi_operations.yml")
    dest_dir = os.path.join(app_path, "config")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, "okapi_operations.yml"))

    payload = OkapiOperationRegistry(app_path).list_for_api()
    ids = {row["id"] for row in payload["operations"]}
    assert "convert" in ids
    assert "merge" in ids

"""Tests for pipeline template manager."""

from ldw_core.okapi.template_manager import PipelineTemplateManager


def test_validate_template_requires_steps(app_path):
    mgr = PipelineTemplateManager(app_path)
    errors = mgr.validate({"id": "x", "name": "X", "steps": []})
    assert any("step" in e for e in errors)


def test_save_and_list_user_template(app_path):
    mgr = PipelineTemplateManager(app_path)
    saved = mgr.save_user_template(
        {
            "id": "user_test",
            "name": "User Test",
            "description": "test",
            "steps": [{"id": "s1", "type": "okapi", "operation": "convert"}],
        }
    )
    assert saved["source"] == "user"
    found = mgr.get("user_test")
    assert found is not None
    assert mgr.delete_user_template("user_test") is True

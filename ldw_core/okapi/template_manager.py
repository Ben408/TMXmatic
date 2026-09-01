"""User pipeline template storage (import/export/validate)."""

from __future__ import annotations

import json
import os
from typing import Any

from ldw_core.paths import get_application_path


class PipelineTemplateManager:
    """Built-in templates under ``config/`` plus user templates under ``data/pipeline_templates/``."""

    def __init__(self, app_path: str | None = None) -> None:
        self._app_path = app_path or get_application_path()
        self._builtin_dir = os.path.join(self._app_path, "config", "pipeline_templates")
        self._user_dir = os.path.join(self._app_path, "data", "pipeline_templates")
        os.makedirs(self._user_dir, exist_ok=True)

    def list_all(self) -> list[dict[str, Any]]:
        templates: list[dict[str, Any]] = []
        for directory, source in ((self._builtin_dir, "builtin"), (self._user_dir, "user")):
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(directory, name)
                with open(path, encoding="utf-8") as handle:
                    row = json.load(handle)
                row.setdefault("source", source)
                templates.append(row)
        return templates

    def get(self, template_id: str) -> dict[str, Any] | None:
        for row in self.list_all():
            if row.get("id") == template_id:
                return row
        return None

    def save_user_template(self, template: dict[str, Any]) -> dict[str, Any]:
        """Persist a user-authored template; returns validation errors if any."""
        errors = self.validate(template)
        if errors:
            raise ValueError("; ".join(errors))
        template_id = template["id"]
        path = os.path.join(self._user_dir, f"{template_id}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(template, handle, indent=2)
            handle.write("\n")
        template["source"] = "user"
        return template

    def delete_user_template(self, template_id: str) -> bool:
        path = os.path.join(self._user_dir, f"{template_id}.json")
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False

    @staticmethod
    def validate(template: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not template.get("id"):
            errors.append("template id required")
        if not template.get("name"):
            errors.append("template name required")
        steps = template.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append("at least one pipeline step required")
        else:
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"step {index + 1} must be an object")
                    continue
                if not step.get("type"):
                    errors.append(f"step {index + 1} missing type")
                if not step.get("operation"):
                    errors.append(f"step {index + 1} missing operation")
        return errors

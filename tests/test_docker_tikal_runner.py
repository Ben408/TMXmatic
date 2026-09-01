"""Docker tikal runner health probe tests."""

from unittest.mock import patch

from ldw_core.okapi.runners import DockerTikalRunner


def test_docker_health_requires_image_and_tikal_probe():
    runner = DockerTikalRunner("ldw-okapi-tikal:1.48")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ARG001
        calls.append(cmd)
        result = type("R", (), {})()
        result.returncode = 0
        result.stdout = "Okapi"
        result.stderr = ""
        return result

    with patch("ldw_core.okapi.runners.shutil.which", return_value="/usr/bin/docker"):
        with patch("ldw_core.okapi.runners.subprocess.run", side_effect=fake_run):
            health = runner.health_check()

    assert health.available is True
    assert "tikal ready" in health.message
    assert calls[0][:2] == ["docker", "info"]
    assert calls[1][:3] == ["docker", "image", "inspect"]
    assert calls[2][:5] == ["docker", "run", "--rm", "ldw-okapi-tikal:1.48", "tikal"]


def test_docker_health_missing_image():
    runner = DockerTikalRunner("ldw-okapi-tikal:missing")

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ARG001
        result = type("R", (), {})()
        if cmd[:3] == ["docker", "image", "inspect"]:
            result.returncode = 1
        else:
            result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("ldw_core.okapi.runners.shutil.which", return_value="/usr/bin/docker"):
        with patch("ldw_core.okapi.runners.subprocess.run", side_effect=fake_run):
            health = runner.health_check()

    assert health.available is False
    assert "not found" in health.message

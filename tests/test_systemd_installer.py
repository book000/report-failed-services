import os
import shutil
import subprocess
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "SystemdFiles"


def run_installer(tmp_path, name="project with spaces & # % \" $ and \\ slash", fail=""):
    project = tmp_path / name
    units = project / "SystemdFiles"
    shutil.copytree(SOURCE, units)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    capture = tmp_path / "capture"
    capture.mkdir(exist_ok=True)
    sudo = bin_dir / "sudo"
    sudo.write_text(
        '#!/bin/bash\n'
        'printf "%s\\n" "$*" >> "$CAPTURE/calls"\n'
        'if [[ "$*" == *"$FAIL"* && -n "$FAIL" ]]; then exit 42; fi\n'
        'if [[ "$1" == cp && "$4" == *.service ]]; then '
        'cp -- "$4" "$CAPTURE/service"; fi\n'
    )
    sudo.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
               CAPTURE=str(capture), FAIL=fail)
    result = subprocess.run(["bash", str(units / "install-systemd.sh")],
                            env=env, capture_output=True, text=True)
    return project, capture, result


def test_installer_renders_special_path_and_runs_timer(tmp_path):
    project, capture, result = run_installer(tmp_path)
    assert result.returncode == 0, result.stderr
    rendered = (capture / "service").read_text()
    escaped = str(project).replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    assert f'WorkingDirectory="{escaped}"' in rendered
    assert f'ExecStart="{escaped.replace("$", "$$")}/venv/bin/python" -m src' in rendered
    assert "%WorkingDirectory%" in (project / "SystemdFiles/report-failed-services.service").read_text()
    calls = (capture / "calls").read_text().splitlines()
    assert calls[-3:] == ["systemctl daemon-reload", "systemctl enable report-failed-services.timer",
                          "systemctl start report-failed-services.timer"]


@pytest.mark.parametrize("fail", [".service", ".timer", "daemon-reload", "enable", "start"])
def test_installer_stops_when_command_fails(tmp_path, fail):
    _, capture, result = run_installer(tmp_path, fail=fail)
    assert result.returncode == 42
    assert fail in (capture / "calls").read_text().splitlines()[-1]


def test_installer_requires_timer(tmp_path):
    project = tmp_path / "project"
    units = project / "SystemdFiles"
    shutil.copytree(SOURCE, units)
    (units / "report-failed-services.timer").unlink()
    result = subprocess.run(["bash", str(units / "install-systemd.sh")],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "Service and timer files are required" in result.stderr

"""Tests for impe/runner.py — run_script()."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from impe.runner import run_script


@pytest.mark.parametrize("returncode", [0, 1, 2])
def test_run_script_exit_code(returncode):
    with patch("subprocess.run", return_value=MagicMock(returncode=returncode)):
        rc = run_script("GetNPUsers", ["impacket-GetNPUsers"], None)
    assert rc == returncode


@pytest.mark.parametrize("timeout", [30, 60, None])
def test_run_script_timeout_arg(timeout):
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        run_script("GetNPUsers", ["impacket-GetNPUsers"], timeout=timeout)
    assert mock_run.call_args[1].get("timeout") == timeout


def test_run_script_timeout_behavior(capsys):
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=5)
    ):
        rc = run_script("GetNPUsers", ["impacket-GetNPUsers"], timeout=5)
    assert rc == -1
    assert "timed out" in capsys.readouterr().out.lower()


@pytest.mark.parametrize(
    "timeout, expect_value, reject_token",
    [
        pytest.param(45, "45", None, id="shows-value"),
        pytest.param(None, None, "Timeout", id="omitted-when-none"),
    ],
)
def test_run_script_timeout_display(timeout, expect_value, reject_token, capsys):
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        run_script("GetNPUsers", ["impacket-GetNPUsers"], timeout=timeout)
    out = capsys.readouterr().out
    if expect_value is not None:
        assert expect_value in out
    if reject_token is not None:
        assert reject_token not in out


def test_run_script_file_not_found(capsys):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as exc_info:
            run_script("GetNPUsers", ["impacket-GetNPUsers"], None)
    assert exc_info.value.code == 1
    assert "not found" in capsys.readouterr().out.lower()


def test_run_script_exits_130_on_interrupt():
    with patch("subprocess.run", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as exc_info:
            run_script("GetNPUsers", ["impacket-GetNPUsers"], None)
    assert exc_info.value.code == 130


def test_run_script_passes_cmd():
    cmd = ["impacket-GetNPUsers", "corp.local/admin:pass", "-dc-ip", "10.0.0.1"]
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        run_script("GetNPUsers", cmd, timeout=None)
    assert mock_run.call_args[0][0] == cmd


def test_run_script_prints_separator(capsys):
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        run_script("GetNPUsers", ["impacket-GetNPUsers"], None)
    out = capsys.readouterr().out
    assert "GetNPUsers" in out
    assert "─" in out

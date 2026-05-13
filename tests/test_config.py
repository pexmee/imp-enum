"""Tests for impe/config.py — create_default_config(), deep_merge(), load_config()."""

import json
import tempfile

import pytest

from impe.config import create_default_config, deep_merge, load_config
from impe.scripts import SCRIPT_NAMES


@pytest.mark.parametrize(
    "key, expected",
    [
        ("target", None),
        ("domain", None),
        ("username", None),
        ("password", None),
        ("hashes", None),
        ("no_pass", False),
        ("kerberos", False),
        ("aes_key", None),
        ("dc_host", None),
        ("scripts", "all"),
        ("script_timeout", None),
        ("output_file", None),
    ],
)
def test_default_config_value(key, expected):
    assert create_default_config()[key] == expected


def test_default_config_script_flags_has_all_scripts():
    cfg = create_default_config()
    for name in SCRIPT_NAMES:
        assert name in cfg["script_flags"], f"script_flags missing {name!r}"


def test_default_config_script_flags_empty_strings():
    cfg = create_default_config()
    for name, flags in cfg["script_flags"].items():
        assert flags == "", (
            f"script_flags[{name!r}] should be empty string, got {flags!r}"
        )


def test_default_config_returns_new_object():
    a = create_default_config()
    b = create_default_config()
    assert a is not b
    a["target"] = "mutated"
    assert b["target"] is None


def test_deep_merge_simple_override():
    base = {"a": 1, "b": 2}
    result = deep_merge(base, {"b": 99})
    assert result["a"] == 1
    assert result["b"] == 99


def test_deep_merge_nested_dict():
    base = {"flags": {"k": False, "v": False}}
    result = deep_merge(base, {"flags": {"k": True}})
    assert result["flags"]["k"] is True
    assert result["flags"]["v"] is False


def test_deep_merge_none_does_not_overwrite():
    base = {"target": "10.0.0.1"}
    result = deep_merge(base, {"target": None})
    assert result["target"] == "10.0.0.1"


def test_deep_merge_does_not_mutate_base():
    base = {"a": 1}
    deep_merge(base, {"a": 99})
    assert base["a"] == 1


def test_deep_merge_adds_new_key():
    result = deep_merge({"a": 1}, {"b": 2})
    assert result["b"] == 2


def test_deep_merge_script_flags():
    base = create_default_config()
    result = deep_merge(base, {"script_flags": {"GetNPUsers": "-request"}})
    assert result["script_flags"]["GetNPUsers"] == "-request"
    assert result["script_flags"]["GetUserSPNs"] == ""


def test_load_config_valid_json():
    data = {"target": "192.168.1.1", "domain": "test.local"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        fname = f.name
    loaded = load_config(fname)
    assert loaded["target"] == "192.168.1.1"
    assert loaded["domain"] == "test.local"


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


def test_load_config_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        fname = f.name
    with pytest.raises(json.JSONDecodeError):
        load_config(fname)


def test_load_and_merge_with_defaults():
    data = {"domain": "corp.local", "username": "admin"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        fname = f.name
    cfg = deep_merge(create_default_config(), load_config(fname))
    assert cfg["domain"] == "corp.local"
    assert cfg["username"] == "admin"
    assert cfg["target"] is None
    assert cfg["scripts"] == "all"

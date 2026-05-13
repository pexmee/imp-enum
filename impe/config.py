"""Config schema, JSON loading, and deep-merge helpers."""

import json
from typing import Any

from .scripts import SCRIPT_NAMES


def create_default_config() -> dict[str, Any]:
    """Return a fully-populated config dict with all keys set to safe defaults."""
    return {
        "target": None,  # DC IP or hostname
        "domain": None,  # AD domain name, e.g. corp.local
        "username": None,
        "password": None,
        "hashes": None,  # LMHASH:NTHASH for pass-the-hash
        "no_pass": False,  # Skip password (AS-REP roasting etc.)
        "kerberos": False,
        "aes_key": None,  # AES key for Kerberos
        "dc_host": None,  # DC hostname (for Kerberos when target is IP)
        "scripts": "all",
        "script_timeout": None,
        "output_file": None,
        "script_flags": {name: "" for name in SCRIPT_NAMES},
    }


def load_config(path: str) -> dict[str, Any]:
    """Load and return a config dict from a JSON file."""
    with open(path) as fh:
        return json.load(fh)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with *override* merged into *base*.

    Nested dicts are merged recursively.  ``None`` values in *override* are
    skipped so that missing-or-null JSON fields do not clobber defaults.
    """
    result = base.copy()
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], val)
        elif val is not None:
            result[key] = val
    return result

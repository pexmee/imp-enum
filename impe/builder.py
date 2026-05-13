"""Translate a config dict into an impacket command argument list."""

import shlex
from typing import Any

from .scripts import ScriptInfo


def build_command(script: ScriptInfo, cfg: dict[str, Any]) -> list[str]:
    """Return the full impacket argument list for script from cfg."""
    cmd: list[str] = [script.binary]

    target = cfg.get("target") or ""
    domain = cfg.get("domain") or ""
    username = cfg.get("username") or ""
    password = cfg.get("password")
    hashes = cfg.get("hashes")
    no_pass = cfg.get("no_pass", False)
    kerberos = cfg.get("kerberos", False)
    aes_key = cfg.get("aes_key")
    dc_host = cfg.get("dc_host")

    # Build the "domain/username" prefix; include password inline only when
    # no alternative auth method is active.
    cred_base = f"{domain}/{username}" if domain else username
    if password and not hashes and not no_pass:
        cred_str = f"{cred_base}:{password}"
    else:
        cred_str = cred_base

    has_creds = bool(domain or username)

    if script.target_type == "dc":
        cmd.append(cred_str)
        if target:
            cmd.extend(["-dc-ip", target])
        if dc_host and script.supports_dc_host:
            cmd.extend(["-dc-host", dc_host])

    elif script.target_type == "target_flag":
        # No credentials — binary only accepts -target <ip>
        if target:
            cmd.extend(["-target", target])

    elif script.target_type == "host_at":
        if target:
            cmd.append(f"{cred_str}@{target}")
        elif has_creds:
            cmd.append(cred_str)

    elif script.target_type == "host":
        if has_creds and target:
            cmd.append(f"{cred_str}@{target}")
        elif target:
            cmd.append(target)
        elif has_creds:
            cmd.append(cred_str)

    # Shared auth flags — not applicable to target_flag scripts (no credential interface)
    if script.target_type != "target_flag":
        if hashes:
            cmd.extend(["-hashes", hashes])
        if no_pass:
            cmd.append("-no-pass")
        if kerberos:
            cmd.append("-k")
        if aes_key:
            cmd.extend(["-aesKey", aes_key])

    # Per-script extra flags appended last
    script_flags_str = cfg.get("script_flags", {}).get(script.name, "")
    if script_flags_str:
        cmd.extend(shlex.split(script_flags_str))

    return cmd

"""Impacket script registry and selection parser."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptInfo:
    """Metadata for a single impacket enumeration script."""

    name: str
    binary: str
    target_type: str  # "dc" | "host_at" | "host" | "target_flag"
    # Whether the binary accepts -dc-host (Kerberos hostname override).
    # Most LDAP-based dc scripts do; Kerberos-native tools and host scanners do not.
    supports_dc_host: bool = True


# dc:          positional "domain/user[:pass]", appends -dc-ip <target> [-dc-host]
# host_at:     positional "domain/user[:pass]@host"
# host:        positional "[domain/user[:pass]@]host" (creds optional)
# target_flag: no credentials; appends -target <target> only

ALL_SCRIPTS: list[ScriptInfo] = [
    # DC-based (LDAP): support both -dc-ip and -dc-host
    ScriptInfo("GetNPUsers", "impacket-GetNPUsers", "dc"),
    ScriptInfo("GetUserSPNs", "impacket-GetUserSPNs", "dc"),
    ScriptInfo("GetADUsers", "impacket-GetADUsers", "dc"),
    ScriptInfo("GetADComputers", "impacket-GetADComputers", "dc"),
    ScriptInfo("GetLAPSPassword", "impacket-GetLAPSPassword", "dc"),
    ScriptInfo("findDelegation", "impacket-findDelegation", "dc"),
    # DC-based (Kerberos-native / host scanner): only -dc-ip, not -dc-host
    ScriptInfo("getTGT", "impacket-getTGT", "dc", supports_dc_host=False),
    ScriptInfo("netview", "impacket-netview", "dc", supports_dc_host=False),
    # host_at-based: positional "domain/user[:pass]@host"
    ScriptInfo("Get-GPPPassword", "impacket-Get-GPPPassword", "host_at"),
    ScriptInfo("samrdump", "impacket-samrdump", "host_at"),
    ScriptInfo("lookupsid", "impacket-lookupsid", "host_at"),
    ScriptInfo("rdp_check", "impacket-rdp_check", "host_at"),
    ScriptInfo("wmiquery", "impacket-wmiquery", "host_at"),
    # host-based: positional "[domain/user[:pass]@]host" (creds optional)
    ScriptInfo("rpcdump", "impacket-rpcdump", "host"),
    # target_flag: no credentials; passes -target <ip> only
    ScriptInfo("getArch", "impacket-getArch", "target_flag"),
]

SCRIPT_NAMES: list[str] = [s.name for s in ALL_SCRIPTS]

_BY_NAME: dict[str, ScriptInfo] = {s.name: s for s in ALL_SCRIPTS}
_NAME_IDX: dict[str, int] = {s.name.lower(): i for i, s in enumerate(ALL_SCRIPTS)}


def get_script(name: str) -> ScriptInfo | None:
    """Return the ScriptInfo for *name* (case-insensitive), or None."""
    idx = _NAME_IDX.get(name.lower())
    return ALL_SCRIPTS[idx] if idx is not None else None


def parse_scripts(selection: str) -> list[ScriptInfo]:
    """Resolve a selection string to an ordered list of ScriptInfo objects.

    Tokens are comma-separated.  Supported forms:

    - ``all`` / ``*``        — every script (default)
    - ``1-3``                — inclusive range by 1-based index
    - ``1,3,5``              — explicit indices
    - ``GetNPUsers``         — exact name (case-insensitive)
    - ``-2``                 — exclude index 2
    - ``-GetNPUsers``        — exclude by name
    """
    if not selection or selection.strip().lower() in ("all", "*"):
        return list(ALL_SCRIPTS)

    parts = [p.strip() for p in selection.split(",") if p.strip()]
    include: set[int] = set()
    exclude: set[int] = set()

    for part in parts:
        if part.startswith("-"):
            token = part[1:]
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(ALL_SCRIPTS):
                    exclude.add(idx)
            elif token.lower() in _NAME_IDX:
                exclude.add(_NAME_IDX[token.lower()])
        else:
            # Try exact script name first (handles names with dashes like Get-GPPPassword)
            if part.lower() in _NAME_IDX:
                include.add(_NAME_IDX[part.lower()])
            elif part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(ALL_SCRIPTS):
                    include.add(idx)
            else:
                # Try numeric range: "1-3" — split on first dash only when both sides are digits
                dash_pos = part.find("-")
                if dash_pos > 0:
                    lo_str, hi_str = part[:dash_pos], part[dash_pos + 1 :]
                    if lo_str.isdigit() and hi_str.isdigit():
                        for i in range(int(lo_str) - 1, int(hi_str)):
                            if 0 <= i < len(ALL_SCRIPTS):
                                include.add(i)

    if include:
        selected = include - exclude
    else:
        selected = set(range(len(ALL_SCRIPTS))) - exclude

    return [ALL_SCRIPTS[i] for i in sorted(selected)]

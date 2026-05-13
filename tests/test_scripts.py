"""Tests for impe/scripts.py — ALL_SCRIPTS registry and parse_scripts()."""

import pytest

from impe.scripts import ALL_SCRIPTS, SCRIPT_NAMES, get_script, parse_scripts


def test_all_scripts_nonempty():
    assert len(ALL_SCRIPTS) > 0


def test_all_scripts_unique_names():
    names = [s.name for s in ALL_SCRIPTS]
    assert len(names) == len(set(names))


def test_all_scripts_unique_binaries():
    binaries = [s.binary for s in ALL_SCRIPTS]
    assert len(binaries) == len(set(binaries))


def test_all_scripts_valid_target_types():
    valid = {"dc", "host_at", "host", "target_flag"}
    for s in ALL_SCRIPTS:
        assert s.target_type in valid, (
            f"{s.name} has unknown target_type {s.target_type!r}"
        )


def test_script_names_list_matches():
    assert SCRIPT_NAMES == [s.name for s in ALL_SCRIPTS]


@pytest.mark.parametrize(
    "name",
    [
        "GetNPUsers",
        "GetUserSPNs",
        "GetADUsers",
        "GetADComputers",
        "GetLAPSPassword",
        "findDelegation",
        "getTGT",
        "netview",
        "Get-GPPPassword",
        "samrdump",
        "lookupsid",
        "rdp_check",
        "wmiquery",
        "rpcdump",
        "getArch",
    ],
)
def test_known_script_registered(name):
    assert name in SCRIPT_NAMES


@pytest.mark.parametrize(
    "name, expected_type",
    [
        ("GetNPUsers", "dc"),
        ("GetUserSPNs", "dc"),
        ("findDelegation", "dc"),
        ("getTGT", "dc"),
        ("netview", "dc"),
        ("Get-GPPPassword", "host_at"),
        ("samrdump", "host_at"),
        ("lookupsid", "host_at"),
        ("rdp_check", "host_at"),
        ("wmiquery", "host_at"),
        ("rpcdump", "host"),
        ("getArch", "target_flag"),
    ],
)
def test_script_target_type(name, expected_type):
    s = get_script(name)
    assert s is not None
    assert s.target_type == expected_type


@pytest.mark.parametrize(
    "name, expected",
    [
        ("GetNPUsers", True),
        ("GetUserSPNs", True),
        ("GetADUsers", True),
        ("GetADComputers", True),
        ("GetLAPSPassword", True),
        ("findDelegation", True),
        ("getTGT", False),
        ("netview", False),
    ],
)
def test_supports_dc_host(name, expected):
    s = get_script(name)
    assert s is not None
    assert s.supports_dc_host is expected


@pytest.mark.parametrize(
    "lookup, expected_name, expected_binary",
    [
        ("GetNPUsers", "GetNPUsers", "impacket-GetNPUsers"),
        ("getnpusers", "GetNPUsers", "impacket-GetNPUsers"),  # case-insensitive
        ("Get-GPPPassword", "Get-GPPPassword", "impacket-Get-GPPPassword"),
    ],
)
def test_get_script_lookup(lookup, expected_name, expected_binary):
    s = get_script(lookup)
    assert s is not None
    assert s.name == expected_name
    assert s.binary == expected_binary


def test_get_script_unknown():
    assert get_script("nonexistent") is None


@pytest.mark.parametrize(
    "selection, expected_names",
    [
        # "all" selectors
        pytest.param("all", [s.name for s in ALL_SCRIPTS], id="keyword-all"),
        pytest.param("*", [s.name for s in ALL_SCRIPTS], id="keyword-star"),
        pytest.param("", [s.name for s in ALL_SCRIPTS], id="empty-string"),
        # by name
        pytest.param("GetNPUsers", ["GetNPUsers"], id="single-name"),
        pytest.param("getnpusers", ["GetNPUsers"], id="name-case-insensitive"),
        pytest.param("Get-GPPPassword", ["Get-GPPPassword"], id="name-with-dash"),
        pytest.param(
            "GetNPUsers,GetUserSPNs", ["GetNPUsers", "GetUserSPNs"], id="multiple-names"
        ),
        pytest.param("samrdump,lookupsid", ["samrdump", "lookupsid"], id="two-host-at"),
        pytest.param("rpcdump", ["rpcdump"], id="single-host"),
        # by index
        pytest.param("1", [ALL_SCRIPTS[0].name], id="single-index"),
        pytest.param("1-2", ["GetNPUsers", "GetUserSPNs"], id="range-1-2"),
        pytest.param(
            "1,3", [ALL_SCRIPTS[0].name, ALL_SCRIPTS[2].name], id="explicit-indices"
        ),
        # out-of-range index: nothing matched → falls back to all
        pytest.param("999", [s.name for s in ALL_SCRIPTS], id="out-of-range"),
    ],
)
def test_parse_selection(selection, expected_names):
    result = parse_scripts(selection)
    assert [s.name for s in result] == expected_names


@pytest.mark.parametrize(
    "selection, excluded_name",
    [
        pytest.param("-1", ALL_SCRIPTS[0].name, id="exclude-by-index"),
        pytest.param("-GetNPUsers", "GetNPUsers", id="exclude-by-name"),
        pytest.param(
            "-Get-GPPPassword", "Get-GPPPassword", id="exclude-name-with-dash"
        ),
    ],
)
def test_parse_excludes_script(selection, excluded_name):
    result = parse_scripts(selection)
    names = {s.name for s in result}
    assert excluded_name not in names
    assert len(result) == len(ALL_SCRIPTS) - 1


def test_parse_range_full():
    n = len(ALL_SCRIPTS)
    assert parse_scripts(f"1-{n}") == ALL_SCRIPTS


def test_parse_range_with_exclusion():
    result = parse_scripts("1-3,-2")
    assert ALL_SCRIPTS[0] in result
    assert ALL_SCRIPTS[1] not in result
    assert ALL_SCRIPTS[2] in result


def test_parse_preserves_order():
    result = parse_scripts("3,1,2")
    indices = [ALL_SCRIPTS.index(s) for s in result]
    assert indices == sorted(indices)

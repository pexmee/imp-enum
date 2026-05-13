"""Tests for impe/builder.py — build_command()."""

import pytest

from impe.builder import build_command
from impe.config import create_default_config
from impe.scripts import get_script

_NP_USERS = get_script("GetNPUsers")  # dc
_USER_SPNS = get_script("GetUserSPNs")  # dc
_AD_USERS = get_script("GetADUsers")  # dc
_SAMRDUMP = get_script("samrdump")  # host_at
_LOOKUPSID = get_script("lookupsid")  # host_at
_GPP_PASS = get_script("Get-GPPPassword")  # host_at
_RPCDUMP = get_script("rpcdump")  # host
_GETARCH = get_script("getArch")  # target_flag


def _cfg(**overrides):
    cfg = create_default_config()
    cfg.update(overrides)
    return cfg


class TestDcScripts:
    def test_basic_password_auth(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(_NP_USERS, cfg)
        assert cmd[0] == "impacket-GetNPUsers"
        assert "corp.local/admin:pass" in cmd
        assert "-dc-ip" in cmd
        assert cmd[cmd.index("-dc-ip") + 1] == "10.0.0.1"

    def test_credentials_format(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="user", password="secret"
        )
        cmd = build_command(_NP_USERS, cfg)
        assert cmd[1] == "corp.local/user:secret"

    def test_no_password_in_cred_when_hashes(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            password="ignored",
            hashes=":NTHASH",
        )
        cmd = build_command(_NP_USERS, cfg)
        assert ":ignored" not in cmd[1]
        assert "-hashes" in cmd
        assert cmd[cmd.index("-hashes") + 1] == ":NTHASH"

    def test_no_password_in_cred_when_no_pass(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="user",
            password="secret",
            no_pass=True,
        )
        assert ":secret" not in build_command(_NP_USERS, cfg)[1]

    def test_no_target_omits_dc_ip(self):
        cfg = _cfg(domain="corp.local", username="user", password="pass")
        assert "-dc-ip" not in build_command(_NP_USERS, cfg)

    def test_per_script_flags(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="user",
            password="pass",
            script_flags={"GetNPUsers": "-request -format hashcat"},
        )
        cmd = build_command(_NP_USERS, cfg)
        assert "-request" in cmd
        assert "-format" in cmd
        assert "hashcat" in cmd

    def test_per_script_flags_not_applied_to_other_scripts(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="user",
            password="pass",
            script_flags={
                "GetNPUsers": "-request",
                "GetUserSPNs": "-outputfile out.txt",
            },
        )
        cmd = build_command(_USER_SPNS, cfg)
        assert "-request" not in cmd
        assert "-outputfile" in cmd

    @pytest.mark.parametrize(
        "script_name",
        [
            "GetNPUsers",
            "GetUserSPNs",
            "GetADUsers",
            "GetADComputers",
            "GetLAPSPassword",
            "findDelegation",
            "getTGT",
            "netview",
        ],
    )
    def test_dc_script_command(self, script_name):
        script = get_script(script_name)
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(script, cfg)
        assert cmd[0] == f"impacket-{script_name}"
        assert "-dc-ip" in cmd
        assert cmd[cmd.index("-dc-ip") + 1] == "10.0.0.1"

    @pytest.mark.parametrize(
        "script_name",
        [
            "GetNPUsers",
            "GetUserSPNs",
            "GetADUsers",
            "GetADComputers",
            "GetLAPSPassword",
            "findDelegation",
        ],
    )
    def test_dc_host_passed_when_supported(self, script_name):
        script = get_script(script_name)
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            password="pass",
            dc_host="dc01.corp.local",
        )
        cmd = build_command(script, cfg)
        assert "-dc-host" in cmd
        assert cmd[cmd.index("-dc-host") + 1] == "dc01.corp.local"

    @pytest.mark.parametrize("script_name", ["getTGT", "netview"])
    def test_dc_host_omitted_when_not_supported(self, script_name):
        script = get_script(script_name)
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            password="pass",
            dc_host="dc01.corp.local",
        )
        assert "-dc-host" not in build_command(script, cfg)


class TestHostAtScripts:
    def test_target_format(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(_SAMRDUMP, cfg)
        assert cmd[0] == "impacket-samrdump"
        assert cmd[1] == "corp.local/admin:pass@10.0.0.1"

    def test_no_dc_ip_flag(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        assert "-dc-ip" not in build_command(_SAMRDUMP, cfg)

    def test_hash_auth_format(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", hashes=":NTHASH"
        )
        cmd = build_command(_SAMRDUMP, cfg)
        assert cmd[1] == "corp.local/admin@10.0.0.1"
        assert "-hashes" in cmd

    def test_no_target_omits_at(self):
        cfg = _cfg(domain="corp.local", username="admin", password="pass")
        assert "@" not in build_command(_SAMRDUMP, cfg)[1]

    @pytest.mark.parametrize(
        "script_name",
        [
            "Get-GPPPassword",
            "samrdump",
            "lookupsid",
            "rdp_check",
            "wmiquery",
        ],
    )
    def test_host_at_command(self, script_name):
        script = get_script(script_name)
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(script, cfg)
        assert cmd[0] == f"impacket-{script_name}"
        assert "@10.0.0.1" in cmd[1]


class TestTargetFlagScripts:
    def test_target_passed_as_flag(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(_GETARCH, cfg)
        assert cmd[0] == "impacket-getArch"
        assert "-target" in cmd
        assert cmd[cmd.index("-target") + 1] == "10.0.0.1"

    def test_no_credentials_in_command(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(_GETARCH, cfg)
        assert not any("corp.local" in tok or "admin" in tok for tok in cmd)

    def test_no_auth_flags(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            hashes=":NTHASH",
            kerberos=True,
        )
        cmd = build_command(_GETARCH, cfg)
        for flag in ("-hashes", "-no-pass", "-k", "-aesKey"):
            assert flag not in cmd

    def test_no_target_produces_binary_only(self):
        assert build_command(_GETARCH, _cfg()) == ["impacket-getArch"]


class TestHostScripts:
    def test_with_creds_and_target(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        cmd = build_command(_RPCDUMP, cfg)
        assert cmd[0] == "impacket-rpcdump"
        assert cmd[1] == "corp.local/admin:pass@10.0.0.1"

    def test_no_creds_just_target(self):
        assert build_command(_RPCDUMP, _cfg(target="10.0.0.1"))[1] == "10.0.0.1"

    def test_no_creds_no_target(self):
        assert build_command(_RPCDUMP, _cfg()) == ["impacket-rpcdump"]


class TestAuthFlags:
    def test_hashes_flag(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            hashes=":aad3b435b51404eeaad3b435b51404ee",
        )
        cmd = build_command(_NP_USERS, cfg)
        assert "-hashes" in cmd
        assert cmd[cmd.index("-hashes") + 1] == ":aad3b435b51404eeaad3b435b51404ee"

    def test_no_pass_flag(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="user", no_pass=True
        )
        assert "-no-pass" in build_command(_NP_USERS, cfg)

    def test_kerberos_flag(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="user", kerberos=True
        )
        assert "-k" in build_command(_NP_USERS, cfg)

    def test_aes_key(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="user",
            aes_key="abc123",
            kerberos=True,
        )
        cmd = build_command(_NP_USERS, cfg)
        assert "-aesKey" in cmd
        assert cmd[cmd.index("-aesKey") + 1] == "abc123"

    def test_password_excluded_when_hashes_present(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            password="plaintext",
            hashes=":HASH",
        )
        assert ":plaintext" not in " ".join(build_command(_NP_USERS, cfg))

    def test_kerberos_no_pass_no_hash(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", kerberos=True
        )
        cmd = build_command(_NP_USERS, cfg)
        assert "-k" in cmd
        assert "-hashes" not in cmd
        assert "-no-pass" not in cmd

    def test_unused_flags_omitted(self):
        cfg = create_default_config()
        cfg.update({"target": "10.0.0.1", "domain": "corp.local", "username": "admin"})
        cmd = build_command(_NP_USERS, cfg)
        for flag in ("-no-pass", "-k", "-aesKey", "-hashes"):
            assert flag not in cmd

    def test_dc_host(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="user",
            password="pass",
            dc_host="dc01.corp.local",
        )
        cmd = build_command(_NP_USERS, cfg)
        assert "-dc-host" in cmd
        assert cmd[cmd.index("-dc-host") + 1] == "dc01.corp.local"


class TestPerScriptFlags:
    def test_multi_token_flags(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            password="pass",
            script_flags={"GetADUsers": "-all -debug"},
        )
        cmd = build_command(get_script("GetADUsers"), cfg)
        assert "-all" in cmd
        assert "-debug" in cmd

    def test_quoted_value_in_flags(self):
        cfg = _cfg(
            target="10.0.0.1",
            domain="corp.local",
            username="admin",
            password="pass",
            script_flags={"GetNPUsers": "-outputfile '/tmp/out file.txt'"},
        )
        assert "/tmp/out file.txt" in build_command(_NP_USERS, cfg)

    def test_empty_script_flags_omitted(self):
        cfg = _cfg(
            target="10.0.0.1", domain="corp.local", username="admin", password="pass"
        )
        expected_len = len(
            ["impacket-GetNPUsers", "corp.local/admin:pass", "-dc-ip", "10.0.0.1"]
        )
        assert len(build_command(_NP_USERS, cfg)) == expected_len

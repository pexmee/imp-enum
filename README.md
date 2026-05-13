# imp-enum

A Python wrapper around [impacket](https://github.com/fortra/impacket) that
runs multiple enumeration scripts against a target domain in a single command,
with shared credentials, per-script extra flags, and an optional per-script timeout.

## What it does

`imp-enum` calls impacket `Get*` and enumeration executables once per selected script.
For each script it builds the correct impacket invocation from your supplied
credentials, runs it as a subprocess, optionally enforces a script timeout,
and prints a summary at the end.

Features:

- **One command, many scripts.** Pick `all`, a range (`1-3`), an explicit list
  (`GetNPUsers,GetUserSPNs`), or an exclusion (`-s=-rpcdump`).
- **Shared credentials.** Supply domain, username, and password (or NTLM hashes,
  or Kerberos) once; all scripts receive them.
- **Correct target format per script.** DC-based scripts receive `-dc-ip`; `host_at`
  scripts get `domain/user:pass@host`; `target_flag` scripts get `-target <ip>` with
  no credentials — all derived automatically from the same input.
- **`--dc-ip` alias.** The target can be given as a positional argument *or* with
  `--dc-ip <IP>`, matching the impacket flag users already know.
- **Per-script extra flags** via `--<ScriptName>-flags "FLAGS"`.
- **Script timeout** (`--script-timeout`) that kills the current process after N
  seconds and moves on to the next script.
- **JSON config file** via `--config`. Defaults from the file; CLI flags always win.
- **Three help tiers:** brief banner (no args), standard reference (`-h`), full
  manual (`-hh`).

## Scripts included

| # | Script | Type | Notes |
|---|--------|------|-------|
| 1 | GetNPUsers | dc | AS-REP roasting; works without credentials (`--no-pass`) |
| 2 | GetUserSPNs | dc | Kerberoasting; add `-request` via `--GetUserSPNs-flags` |
| 3 | GetADUsers | dc | Enumerate domain users |
| 4 | GetADComputers | dc | Enumerate domain computers |
| 5 | GetLAPSPassword | dc | Read LAPS passwords |
| 6 | findDelegation | dc | Find Kerberos delegation |
| 7 | getTGT | dc† | Request a Kerberos TGT for credential verification |
| 8 | netview | dc† | Enumerate logged-on sessions and shares across the domain |
| 9 | Get-GPPPassword | host\_at | Extract credentials from Group Policy Preferences |
| 10 | samrdump | host\_at | Dump SAM database via SAMR |
| 11 | lookupsid | host\_at | SID brute-force / user enumeration |
| 12 | rdp_check | host\_at | Check whether RDP is enabled |
| 13 | wmiquery | host\_at | Run WMI queries; add `-query` via `--wmiquery-flags` |
| 14 | rpcdump | host | Dump RPC endpoints |
| 15 | getArch | target\_flag | Detect remote host CPU architecture (no credentials needed) |

**dc** — positional `domain/user[:pass]`, appends `-dc-ip <target>` and `-dc-host` (when `--dc-host` is set)  
**dc†** — same as dc but does **not** accept `-dc-host` (Kerberos-native / scanner tools)  
**host\_at** — positional `domain/user[:pass]@<target>`  
**host** — positional `[domain/user[:pass]@]<target>`; credentials optional  
**target\_flag** — passes `-target <ip>` only; ignores credentials

## Requirements

- Python 3.12 or newer.
- Impacket installed and its scripts on your `PATH`.
  Install via: `pipx install impacket` or `uv tool install impacket`
- [uv](https://docs.astral.sh/uv/) (recommended).

Runtime dependencies (installed automatically):

| Package | Purpose |
|---------|---------|
| [rich](https://github.com/Textualize/rich) | Coloured terminal output |
| [rich-argparse](https://github.com/hamdanal/rich-argparse) | Rich-powered help formatter |

## Install as a uv tool

```bash
uv tool install https://github.com/pexmee/imp-enum.git
```

Then run:

```bash
imp-enum -h
```

## Install for development

```bash
git clone https://github.com/pexmee/imp-enum.git
cd imp-enum
uv sync
```

## Usage examples

Quick-start banner (no arguments):

```bash
imp-enum
```

Full enumeration with password auth:

```bash
imp-enum 10.0.0.1 -d corp.local -u admin -p pass
```

AS-REP roasting (no credentials):

```bash
imp-enum 10.0.0.1 -d corp.local --no-pass -s GetNPUsers
```

Kerberoasting only, request TGS tickets:

```bash
imp-enum 10.0.0.1 -d corp.local -u admin -p pass \
    -s GetUserSPNs --GetUserSPNs-flags '-request'
```

Pass-the-hash:

```bash
imp-enum 10.0.0.1 -d corp.local -u admin -H :aad3b435b51404eeaad3b435b51404ee
```

Kerberos authentication (use hostname, not IP):

```bash
imp-enum dc.corp.local -d corp.local -u admin -k --dc-host dc.corp.local
```

LDAP-based DC scripts only (indices 1–6), 60 s per-script timeout:

```bash
imp-enum 10.0.0.1 -d corp.local -u admin -p pass -s 1-6 --script-timeout 60
```

Using `--dc-ip` instead of a positional target:

```bash
imp-enum --dc-ip 10.0.0.1 -d corp.local -u admin -p pass
```

Exclude rpcdump:

```bash
imp-enum 10.0.0.1 -d corp.local -u admin -p pass -s=-rpcdump
```

Load a config, override the target on CLI:

```bash
imp-enum --config corp.json 10.0.0.1
```

## Script selection syntax

Pass to `-s` / `--scripts`. Comma-separated tokens, freely mixed.

| Token | Meaning |
|-------|---------|
| `all` / `*` | Every script (default) |
| `1-3` | Inclusive range by 1-based index |
| `1,3,5` | Explicit indices |
| `GetNPUsers,samrdump` | Explicit names |
| `-s=-3` | Exclude index 3 (use `=` to avoid dash ambiguity) |
| `-s=-rpcdump` | Exclude by name |
| `-s=1-6,-5` | Range with exclusion |

## Per-script flags

Each script has a `--<ScriptName>-flags` option whose value is a single
string, split with `shlex.split` and appended only to that script's invocation:

```bash
--GetNPUsers-flags "-request -format hashcat"
--GetUserSPNs-flags "-request -outputfile spns.txt"
--GetADUsers-flags "-all"
--GetLAPSPassword-flags "-computer-name WS01"
--getTGT-flags "-dc-ip 10.0.0.1"
--samrdump-flags "-csv"
--wmiquery-flags "-query 'SELECT * FROM Win32_Process'"
```

## Config file

```bash
imp-enum --dump-config > my_config.json
# edit my_config.json
imp-enum --config my_config.json 10.0.0.1
```

Top-level JSON keys: `target`, `domain`, `username`, `password`, `hashes`,
`no_pass`, `kerberos`, `aes_key`, `dc_host`, `scripts`, `script_timeout`,
`output_file`, `script_flags` (dict mapping script name → flags string).

CLI flags always override config file values.

## Help levels

| Invocation | Output |
|------------|--------|
| `imp-enum` | Quick-start banner |
| `imp-enum -h` | Standard flag reference |
| `imp-enum -hh` | Full manual: scripts, auth examples, config |
| `imp-enum --dump-config` | Print a config template and exit |

## Development

```bash
uv sync
```

Common tasks via `make`:

```bash
make format   # ruff format .
make lint     # ruff check .
make test     # pytest tests/ -v
```

## Project layout

```
imp-enum/
├── imp_enum.py          Entry point and main() orchestrator
├── impe/                Helper modules
│   ├── scripts.py       Script registry and selection parser
│   ├── config.py        Config schema, JSON load, deep merge
│   ├── builder.py       Builds impacket argv from a config dict
│   ├── runner.py        Subprocess invocation with timeout
│   └── cli.py           argparse setup and CLI-to-config bridge
├── tests/               pytest test suite
│   ├── test_builder.py
│   ├── test_scripts.py
│   ├── test_config.py
│   └── test_runner.py
├── Makefile
├── pyproject.toml
└── README.md
```

## License

See `LICENSE`.

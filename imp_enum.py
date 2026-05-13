#!/usr/bin/env python3

import json
import os
import sys

from impe.builder import build_command
from impe.cli import _console, build_arg_parser, extract_script_flags
from impe.config import create_default_config, deep_merge, load_config
from impe.runner import run_script
from impe.scripts import ALL_SCRIPTS, parse_scripts

_WIDE = "═" * 64
_THIN = "─" * 64

_SCRIPT_IDX: dict[str, int] = {s.name: i for i, s in enumerate(ALL_SCRIPTS)}


def prog_name() -> str:
    return os.path.basename(sys.argv[0]) or "imp-enum"


def _print_brief_usage() -> None:
    p = prog_name()
    build_arg_parser().print_usage(sys.stdout)
    _console.print()
    _console.print("  [bold]quick examples[/bold]")
    _console.print()
    for ex in [
        f"{p} 10.0.0.1 -d corp.local -u admin -p pass",
        f"{p} 10.0.0.1 -d corp.local -u admin -H :NTHASH",
        f"{p} 10.0.0.1 -d corp.local --no-pass -s GetNPUsers",
    ]:
        _console.print(f"    [green]{ex}[/]")
    _console.print()
    _console.print(
        "  [bold cyan]-h[/]  flag reference    "
        "[bold cyan]-hh[/]  full manual    "
        "[bold cyan]--dump-config[/]  config template"
    )
    _console.print()


def _cred_display(value: str | None) -> str:
    if value is None:
        return "(none)"
    if value == "":
        return "(empty)"
    return value


class TeeLogger:
    def __init__(self, filename: str) -> None:
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")
        self.encoding = getattr(self.terminal, "encoding", "utf-8")
        self.errors = getattr(self.terminal, "errors", "replace")

    def write(self, message: str) -> None:
        try:
            self.terminal.write(message)
        except UnicodeEncodeError:
            safe_msg = message.encode(self.encoding, errors="replace").decode(
                self.encoding
            )
            self.terminal.write(safe_msg)
        self.log.write(message)
        self.terminal.flush()
        self.log.flush()

    def flush(self) -> None:
        self.terminal.flush()
        self.log.flush()

    def isatty(self) -> bool:
        if hasattr(self.terminal, "isatty"):
            return self.terminal.isatty()
        return False

    def fileno(self) -> int:
        if hasattr(self.terminal, "fileno"):
            return self.terminal.fileno()
        raise AttributeError("fileno not available")


def print_header(
    target: str,
    domain: str | None,
    username: str | None,
    password: str | None,
    hashes: str | None,
    scripts: list,
    timeout: int | None,
) -> None:
    script_display = ", ".join(f"{_SCRIPT_IDX[s.name] + 1}.{s.name}" for s in scripts)
    print(f"\n{_WIDE}")
    print("  imp-enum")
    print(_WIDE)
    print(f"  Target   : {target or '(none)'}")
    print(f"  Domain   : {_cred_display(domain)}")
    print(f"  Username : {_cred_display(username)}")
    if hashes:
        print(f"  Hashes   : {hashes}")
    else:
        print(f"  Password : {_cred_display(password)}")
    print(f"  Scripts  : {script_display}")
    print(f"  S-Timeout: {f'{timeout}s' if timeout else 'none'}")
    print(_WIDE)


def print_summary(results: dict[str, int]) -> None:
    print(f"\n{_WIDE}")
    print("  Enumeration summary")
    print(_THIN)
    for script_name, rc in results.items():
        if rc == 0:
            status = "OK"
        elif rc == -1:
            status = "TIMEOUT"
        else:
            status = f"FAILED (exit {rc})"
        print(f"  {script_name:<20}  {status}")
    print(f"{_WIDE}\n")


def main() -> None:
    raw = sys.argv[1:]
    parser = build_arg_parser()

    if not raw:
        _print_brief_usage()
        sys.exit(0)

    args = parser.parse_args()

    if args.dump_config:
        print(json.dumps(create_default_config(), indent=2))
        sys.exit(0)

    cfg = create_default_config()

    if args.config:
        cfg = deep_merge(cfg, load_config(args.config))

    for attr, key in [
        ("target", "target"),
        ("domain", "domain"),
        ("username", "username"),
        ("password", "password"),
        ("hashes", "hashes"),
        ("no_pass", "no_pass"),
        ("kerberos", "kerberos"),
        ("aes_key", "aes_key"),
        ("dc_host", "dc_host"),
        ("scripts", "scripts"),
        ("script_timeout", "script_timeout"),
        ("output_file", "output_file"),
    ]:
        val = getattr(args, attr, None)
        if val is not None:
            cfg[key] = val

    # --dc-ip is an explicit alias for the positional target; it wins when set
    if getattr(args, "dc_ip", None) is not None:
        cfg["target"] = args.dc_ip

    for script_name, flags in extract_script_flags(args).items():
        if flags is not None:
            cfg["script_flags"][script_name] = flags

    scripts = parse_scripts(cfg.get("scripts") or "all")
    if not scripts:
        print("[!] No scripts matched the selection — nothing to run.")
        sys.exit(1)

    script_timeout: int | None = cfg.get("script_timeout")
    target = cfg.get("target") or ""
    output_file = cfg.get("output_file")

    if output_file:
        sys.stdout = TeeLogger(output_file)  # type: ignore[assignment]

    print_header(
        target,
        cfg.get("domain"),
        cfg.get("username"),
        cfg.get("password"),
        cfg.get("hashes"),
        scripts,
        script_timeout,
    )

    results: dict[str, int] = {}
    for script in scripts:
        cmd = build_command(script, cfg)
        results[script.name] = run_script(
            script.name,
            cmd,
            script_timeout,
            stream_output=bool(output_file),
        )

    print_summary(results)


if __name__ == "__main__":
    main()

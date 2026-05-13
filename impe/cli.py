"""Argument parser and CLI-to-config bridge."""

import argparse
from typing import Any

from rich.console import Console
from rich.rule import Rule
from rich_argparse import RawDescriptionRichHelpFormatter

from .scripts import ALL_SCRIPTS

_console = Console(highlight=False)


def _print_extra_sections(console: Console, prog: str) -> None:
    """Print the full reference manual sections."""

    def rule(title: str) -> None:
        console.print(Rule(f"[bold cyan]{title}[/]", style="dim"))

    def h(text: str) -> None:
        console.print(f"  [bold white]{text}[/]")

    rule("script selection detail")
    console.print()
    h("Tokens are comma-separated and freely mixed:")
    console.print()
    rows = [
        ("[bold yellow]all[/], [bold yellow]*[/]", "every script (default)"),
        ("[bold yellow]1-3[/]", "inclusive range by 1-based index"),
        ("[bold yellow]1,3,5[/]", "explicit indices"),
        ("[bold yellow]GetNPUsers,GetUserSPNs[/]", "explicit names"),
        ("[bold yellow]-s=-2[/]", "exclude index 2  (use = to avoid dash ambiguity)"),
        ("[bold yellow]-s=-GetNPUsers[/]", "exclude by name"),
        ("[bold yellow]-s=1-6,-3[/]", "range with exclusion"),
    ]
    for flag, desc in rows:
        console.print(f"    {flag:<55}[dim]{desc}[/]")

    console.print()
    h("Scripts:")
    console.print()
    for i, script in enumerate(ALL_SCRIPTS):
        console.print(
            f"    [cyan]{i + 1:2d}.[/] [bold]{script.name:<20}[/]"
            f"  [dim]{script.binary}[/]"
            f"  [italic dim]({script.target_type})[/]"
        )

    console.print()
    rule("authentication")
    console.print()
    rows2 = [
        ("-u admin -p pass", "password auth"),
        ("-u admin -H :NTHASH", "pass-the-hash (NT only, prefix :)"),
        ("-u admin -H LMHASH:NTHASH", "pass-the-hash (LM+NT)"),
        ("--no-pass", "no password — useful with GetNPUsers for AS-REP roasting"),
        ("-u admin -k --dc-host dc.corp.local", "Kerberos (use hostname, not IP)"),
        ("-u admin -k --aesKey <HEX>", "Kerberos with AES key"),
    ]
    for flag, desc in rows2:
        console.print(f"    [bold green]{flag:<45}[/] [dim]{desc}[/]")

    console.print()
    rule("examples")
    console.print()
    examples = [
        (
            "enumerate everything with password",
            f"{prog} 10.0.0.1 -d corp.local -u admin -p pass",
        ),
        (
            "AS-REP roasting — no creds required",
            f"{prog} 10.0.0.1 -d corp.local --no-pass -s GetNPUsers",
        ),
        (
            "Kerberoasting only",
            f"{prog} 10.0.0.1 -d corp.local -u admin -p pass -s GetUserSPNs "
            "--GetUserSPNs-flags '-request'",
        ),
        (
            "pass-the-hash across all scripts",
            f"{prog} 10.0.0.1 -d corp.local -u admin -H :aad3b435b51404eeaad3b435b51404ee",
        ),
        (
            "Kerberos auth with hostname (required for -k)",
            f"{prog} dc.corp.local -d corp.local -u admin -k --dc-host dc.corp.local",
        ),
        (
            "DC-based scripts only (indices 1-6), 60 s timeout",
            f"{prog} 10.0.0.1 -d corp.local -u admin -p pass -s 1-6 --script-timeout 60",
        ),
        (
            "exclude rpcdump",
            f"{prog} 10.0.0.1 -d corp.local -u admin -p pass -s=-rpcdump",
        ),
        (
            "load config, override target on CLI",
            f"{prog} --config corp.json 10.0.0.1",
        ),
    ]
    for comment, cmd in examples:
        console.print(f"  [dim]# {comment}[/]")
        console.print(f"  [green]{cmd}[/]")
        console.print()

    rule("config file")
    console.print()
    console.print(
        "  Generate a template, edit it, then pass with [bold yellow]--config[/]:"
    )
    console.print()
    console.print(f"    [green]{prog} --dump-config > my_config.json[/]")
    console.print()
    console.print(
        "  [dim]Top-level keys: target, domain, username, password, hashes, "
        "no_pass, kerberos, aes_key, dc_host, scripts, script_timeout, "
        "script_flags (dict per script name).[/]"
    )
    console.print()


class ExtendedHelpAction(argparse.Action):
    """Implements ``-hh``: standard help + full reference manual."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: str = argparse.SUPPRESS,
        help: str | None = None,
    ) -> None:
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        parser.print_help()
        _print_extra_sections(_console, parser.prog)
        parser.exit()


def _script_selection_epilog() -> str:
    script_list = "  ".join(
        f"[cyan]{i + 1}.[/][bold]{s.name}[/]" for i, s in enumerate(ALL_SCRIPTS)
    )
    return (
        "[bold]script selection[/]  [dim](-s / --scripts)[/dim]:\n"
        "  [yellow]all[/], [yellow]*[/]          every script (default)\n"
        "  [yellow]1-3[/]             range by index\n"
        "  [yellow]1,3,5[/]           explicit indices\n"
        "  [yellow]GetNPUsers[/]      by name\n"
        "  [yellow]-s=-rpcdump[/]     exclude by name  (use = to avoid dash ambiguity)\n"
        "\n"
        "[bold]scripts[/]:\n"
        f"  {script_list}\n"
        "\n"
        "run [bold cyan]-hh[/] for the full manual\n"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="imp-enum",
        description=(
            "[bold]impacket[/] enumeration wrapper — "
            "run all (or selected) impacket Get/enum scripts in one command."
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
        epilog=_script_selection_epilog(),
    )

    # Extended help
    p.add_argument(
        "-hh",
        action=ExtendedHelpAction,
        help="Show the full reference manual (script list, auth examples, config format)",
    )

    # Core positional + credential flags
    p.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Domain controller IP or hostname",
    )
    p.add_argument(
        "--dc-ip",
        dest="dc_ip",
        default=None,
        metavar="IP",
        help="DC IP address — same as the positional target, accepted for impacket compatibility",
    )
    p.add_argument(
        "-d",
        "--domain",
        default=None,
        metavar="DOMAIN",
        help="Active Directory domain name (e.g. corp.local)",
    )
    p.add_argument(
        "-u",
        "--username",
        default=None,
        metavar="USERNAME",
        help="Username",
    )
    p.add_argument(
        "-p",
        "--password",
        default=None,
        metavar="PASSWORD",
        help="Password",
    )
    p.add_argument(
        "-H",
        "--hashes",
        default=None,
        metavar="LMHASH:NTHASH",
        help="NTLM hashes for pass-the-hash.  Use ':NTHASH' when you only have the NT hash.",
    )
    p.add_argument(
        "--no-pass",
        dest="no_pass",
        action="store_const",
        const=True,
        default=None,
        help="Skip password — useful with GetNPUsers for unauthenticated AS-REP roasting",
    )
    p.add_argument(
        "-k",
        "--kerberos",
        action="store_const",
        const=True,
        default=None,
        help="Use Kerberos authentication (requires a valid TGT or -aesKey)",
    )
    p.add_argument(
        "--aesKey",
        dest="aes_key",
        default=None,
        metavar="HEX_KEY",
        help="AES-128 or AES-256 key for Kerberos (-k required)",
    )
    p.add_argument(
        "--dc-host",
        dest="dc_host",
        default=None,
        metavar="HOSTNAME",
        help="DC hostname for Kerberos (use hostname, not IP, when -k is set)",
    )

    # Script selection and execution
    p.add_argument(
        "-s",
        "--scripts",
        default=None,
        metavar="SELECTION",
        help=(
            'Scripts to run — "all", range (1-3), list (GetNPUsers,GetUserSPNs), '
            "or exclusion (-s=-rpcdump). Default: all."
        ),
    )
    p.add_argument(
        "--script-timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Kill each script process after N seconds and continue",
    )

    # Config / output
    p.add_argument(
        "--config",
        default=None,
        metavar="FILE",
        help="JSON config file — CLI flags always override config values",
    )
    p.add_argument(
        "--dump-config",
        action="store_true",
        help="Print a template JSON config to stdout and exit",
    )
    p.add_argument(
        "--output-file",
        default=None,
        metavar="FILE",
        help="Tee output to FILE while still printing to the console",
    )

    # Per-script extra flags
    sv = p.add_argument_group(
        "per-script flags",
        "Appended only to that script's invocation.  "
        'e.g. [green]--GetNPUsers-flags="-request -format hashcat"[/]',
    )
    for script in ALL_SCRIPTS:
        sv.add_argument(
            f"--{script.name}-flags",
            dest=f"{script.name.replace('-', '_')}_flags",
            default=None,
            metavar="FLAGS",
            help=f"Extra flags for {script.name}",
        )

    return p


def extract_script_flags(args: argparse.Namespace) -> dict[str, str | None]:
    """Return per-script extra-flag strings from *args* (``None`` = unset)."""
    return {
        script.name: getattr(args, f"{script.name.replace('-', '_')}_flags")
        for script in ALL_SCRIPTS
    }

"""Subprocess invocation with optional wall-clock timeout."""

import shlex
import subprocess
import sys
import threading

_SEP = "─" * 64


def run_script(
    script_name: str,
    cmd: list[str],
    timeout: int | None,
    stream_output: bool = False,
) -> int:
    """Invoke an impacket binary and return its exit code."""
    print(f"\n{_SEP}")
    print(f"  Script  : {script_name}")
    print(f"  Command : {shlex.join(cmd)}")
    if timeout:
        print(f"  Timeout : {timeout}s")
    print(_SEP)

    process: subprocess.Popen[str] | None = None

    try:
        if stream_output:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None

            timed_out = False
            timer: threading.Timer | None = None

            if timeout:

                def _timeout_kill() -> None:
                    nonlocal timed_out
                    timed_out = True
                    process.kill()  # type: ignore[union-attr]

                timer = threading.Timer(timeout, _timeout_kill)
                timer.start()

            try:
                for line in process.stdout:
                    sys.stdout.write(line)
            finally:
                if timer is not None:
                    timer.cancel()

            process.wait()

            if timed_out:
                print(f"\n[!] {script_name} timed out after {timeout}s — skipping.")
                return -1

            return process.returncode

        else:
            result = subprocess.run(cmd, timeout=timeout)
            return result.returncode

    except subprocess.TimeoutExpired:
        if process is not None:
            process.kill()
            process.wait()
        print(f"\n[!] {script_name} timed out after {timeout}s — skipping.")
        return -1
    except FileNotFoundError:
        print(
            f"[!] '{cmd[0]}' not found. "
            "Is impacket installed and on PATH? (try: uv tool install impacket)"
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(130)

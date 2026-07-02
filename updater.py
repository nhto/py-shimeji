"""Small helper executable that applies a downloaded release and restarts the app."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from update import copy_release_tree


def _wait_for_processes(exe_name: str, timeout_s: float = 60.0) -> None:
    """Best-effort wait until no process with *exe_name* is running."""
    if sys.platform != "win32":
        time.sleep(2.0)
        return

    deadline = time.monotonic() + timeout_s
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=create_no_window,
        )
        if exe_name.lower() not in result.stdout.lower():
            return
        time.sleep(0.5)
    time.sleep(1.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a py-shimeji release update.")
    parser.add_argument("--source", required=True, help="Extracted release folder")
    parser.add_argument("--target", required=True, help="Install directory to update")
    parser.add_argument("--restart", default="py-shimeji.exe", help="Executable to restart")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    restart_exe = target / args.restart

    if not source.is_dir():
        print(f"Source folder not found: {source}", file=sys.stderr)
        return 1
    if not target.is_dir():
        print(f"Target folder not found: {target}", file=sys.stderr)
        return 1

    _wait_for_processes(args.restart)
    copy_release_tree(source, target)
    if restart_exe.is_file():
        subprocess.Popen(
            [str(restart_exe)],
            cwd=str(target),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

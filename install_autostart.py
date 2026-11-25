#!/usr/bin/env python3
"""Install or remove the per-user launchd agent for the display mode fixer."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path


LABEL = "com.sheet-screen.fix-external-display"
INTERVAL_SECONDS = 3
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs"
DOMAIN = f"gui/{os.getuid()}"


def launchctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["/bin/launchctl", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"launchctl {' '.join(arguments)} failed: {detail}")
    return result


def unload_if_loaded() -> None:
    status = launchctl("print", f"{DOMAIN}/{LABEL}", check=False)
    if status.returncode == 0:
        launchctl("bootout", f"{DOMAIN}/{LABEL}")


def install() -> None:
    script = Path(__file__).with_name("fix_external_display.py").resolve()
    if not script.is_file():
        raise RuntimeError(f"Display fixer script not found: {script}")

    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    configuration = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(script), "--quiet"],
        "RunAtLoad": True,
        "StartInterval": INTERVAL_SECONDS,
        "StandardOutPath": str(LOG_DIR / "fix-external-display.log"),
        "StandardErrorPath": str(LOG_DIR / "fix-external-display-error.log"),
    }

    unload_if_loaded()
    with PLIST_PATH.open("wb") as plist_file:
        plistlib.dump(configuration, plist_file, sort_keys=False)
    launchctl("bootstrap", DOMAIN, str(PLIST_PATH))
    print(
        f"Installed {LABEL}; checks at login and every "
        f"{INTERVAL_SECONDS} seconds."
    )
    print(f"Logs: {LOG_DIR / 'fix-external-display-error.log'}")


def uninstall() -> None:
    unload_if_loaded()
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
    print(f"Removed {LABEL}. Log files were kept in {LOG_DIR}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="stop and remove the launch agent",
    )
    options = parser.parse_args()
    try:
        if options.uninstall:
            uninstall()
        else:
            install()
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

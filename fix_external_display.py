#!/usr/bin/env python3
"""Set external Apple-silicon displays to a compatible 8-bit connection mode."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Display:
    screen_id: str
    name: str


def find_executable(name: str, candidates: tuple[str, ...] = ()) -> str | None:
    executable = shutil.which(name)
    if executable:
        return executable
    return next((candidate for candidate in candidates if shutil.which(candidate)), None)


def run_command(executable: str, *args: str) -> str:
    result = subprocess.run(
        [executable, *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{executable} failed: {detail}")
    return result.stdout.strip()


def external_displays(output: str) -> list[Display]:
    displays = []
    blocks = re.split(r"(?=^Persistent screen id: )", output, flags=re.MULTILINE)
    for block in blocks:
        id_match = re.search(r"^Persistent screen id: (.+)$", block, re.MULTILINE)
        type_match = re.search(r"^Type: (.+)$", block, re.MULTILINE)
        if not id_match or not type_match or "external" not in type_match.group(1).lower():
            continue
        displays.append(Display(id_match.group(1).strip(), type_match.group(1).strip()))
    return displays


def betterdisplay_identifiers(output: str) -> list[dict[str, str]]:
    try:
        identifiers = json.loads(f"[{output}]")
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Could not parse BetterDisplay identifiers: {error}") from error
    if not isinstance(identifiers, list):
        raise RuntimeError("BetterDisplay returned an unexpected identifier list.")
    return identifiers


def active_mode_label(output: str) -> str:
    _, separator, label = output.partition(" - ")
    if not separator or not label.strip():
        raise RuntimeError(f"Could not read the active connection mode: {output}")
    return label.strip()


def mode_labels(output: str) -> list[str]:
    labels = []
    for line in output.splitlines():
        _, separator, label = line.partition(" - ")
        if separator and label.strip():
            labels.append(label.strip())
    return labels


def compatible_eight_bit_mode(active_label: str, available: list[str]) -> bool:
    expected = re.sub(r"\b\d+bit\b", "8bit", active_label, count=1)
    return expected != active_label and expected in available


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Switch external Apple-silicon displays to their matching 8-bit "
            "connection mode through BetterDisplay."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the BetterDisplay command without changing display settings",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress successful status messages",
    )
    options = parser.parse_args()

    def say(message: str) -> None:
        if not options.quiet:
            print(message)

    displayplacer = find_executable(
        "displayplacer",
        ("/opt/homebrew/bin/displayplacer", "/usr/local/bin/displayplacer"),
    )
    betterdisplay = find_executable(
        "betterdisplaycli",
        (
            "/opt/homebrew/bin/betterdisplaycli",
            "/usr/local/bin/betterdisplaycli",
            "/Applications/BetterDisplay.app/Contents/MacOS/BetterDisplay",
        ),
    )
    if not displayplacer:
        print("displayplacer is required. Install it with: brew install displayplacer", file=sys.stderr)
        return 1
    if not betterdisplay:
        print(
            "BetterDisplay CLI is required. Enable CLI access in BetterDisplay settings "
            "or install betterdisplaycli.",
            file=sys.stderr,
        )
        return 1

    try:
        externals = external_displays(run_command(displayplacer, "list"))
        if not externals:
            say("No external displays detected; no change needed.")
            return 0

        identifiers = betterdisplay_identifiers(
            run_command(betterdisplay, "get", "-identifiers")
        )
        by_uuid = {
            entry.get("UUID"): entry
            for entry in identifiers
            if entry.get("UUID") and entry.get("deviceType") == "Display"
        }

        for display in externals:
            info = by_uuid.get(display.screen_id)
            if info is None:
                raise RuntimeError(
                    f"BetterDisplay has no matching record for {display.name} "
                    f"({display.screen_id})."
                )

            selector = f"-UUID={display.screen_id}"
            active = run_command(
                betterdisplay, "get", selector, "-connectionMode"
            )
            active_label = active_mode_label(active)
            say(f"{info.get('name', display.name)}: {active_label}")

            if re.search(r"\b8bit\b", active_label):
                say("Already using an 8-bit connection mode; no change needed.")
                continue

            available = mode_labels(
                run_command(betterdisplay, "get", selector, "-connectionModeList")
            )
            if not compatible_eight_bit_mode(active_label, available):
                raise RuntimeError(
                    f"No matching 8-bit mode is listed for {info.get('name', display.name)}. "
                    "No mode was changed."
                )

            command = [
                betterdisplay,
                "set",
                selector,
                "-connectionMode=bpc:8",
            ]
            if options.dry_run:
                say("Would run:")
                say(shlex.join(command))
                continue

            run_command(*command)
            updated = active_mode_label(
                run_command(betterdisplay, "get", selector, "-connectionMode")
            )
            if not re.search(r"\b8bit\b", updated):
                raise RuntimeError(
                    f"BetterDisplay did not switch {info.get('name', display.name)} "
                    f"to 8-bit mode; current mode is: {updated}"
                )
            say(f"Changed to: {updated}")

        return 0
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# mac_external_monitor_8bit

Made with love by Copilot

# Fixing External Display Mode on macOS

`fix_external_display.py` uses the BetterDisplay CLI to switch external displays on Apple silicon to a compatible 8-bit connection mode. It preserves the current SDR/HDR mode, encoding, range, and other settings, changing only the bit depth. The Mac's built-in display is not changed.

## Usage

Requirements: Python 3, `displayplacer` to detect external displays, and the BetterDisplay CLI with CLI access enabled:

```sh
brew install displayplacer
python3 fix_external_display.py --dry-run
python3 fix_external_display.py
```

`--dry-run` displays the command without changing display settings. The BetterDisplay CLI may be installed with the app or separately through Homebrew. If an 8-bit mode is already active, the utility makes no changes. If no compatible 8-bit mode is available, it exits with an error without changing any settings.

## Start at Login and Fix the Mode After Connecting a Display

The Python script does not need to be compiled. To run the check at macOS login and every 3 seconds:

```sh
python3 install_autostart.py
```

To remove the login item:

```sh
python3 install_autostart.py --uninstall
```

The agent leaves settings unchanged when no external display is connected or the display is already using an 8-bit mode. The 3-second interval provides a quick response after connecting a display without checking every second. Errors are written to `~/Library/Logs/fix-external-display-error.log`.

## Important

`displayplacer` reports framebuffer bit depth, which may differ from the bit depth of the signal sent over the cable. This utility uses BetterDisplay's `connectionMode`, the same connection-mode setting exposed in BetterDisplay's **Color Mode** menu on Apple silicon.

Before changing the mode, the utility checks that BetterDisplay lists an exact 8-bit equivalent of the current mode. It changes only `bpc:8`; encoding, range, chroma sampling, resolution, and refresh rate should remain the same. It does not change the ICC profile.

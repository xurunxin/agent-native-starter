#!/usr/bin/env python3
"""Install a user-local agent-starter launcher for this checkout."""
import os
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(site.USER_BASE) / ("Scripts" if os.name == "nt" else "bin")


def main():
    SCRIPTS.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        launcher = SCRIPTS / "agent-starter.cmd"
        content = f'@"{sys.executable}" "{ROOT / "agent-starter"}" %*\r\n'
    else:
        launcher = SCRIPTS / "agent-starter"
        content = f'#!/bin/sh\nexec "{sys.executable}" "{ROOT / "agent-starter"}" "$@"\n'
    launcher.write_text(content, encoding="utf-8", newline="")
    if os.name != "nt":
        launcher.chmod(0o755)
    print(f"Installed {launcher}")
    print("Add this directory to PATH if the command is not found:")
    print(SCRIPTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the installed Gitleaks binary from PATH or common package-manager locations."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_gitleaks() -> str:
    direct = shutil.which("gitleaks")
    if direct:
        return direct

    candidates: list[Path] = []
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        candidates.extend(packages.glob("Gitleaks.Gitleaks_*/*gitleaks.exe"))
    candidates.extend(
        path
        for root in (os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"))
        if root
        for path in Path(root).glob("Gitleaks*/gitleaks.exe")
    )
    if candidates:
        return str(sorted(candidates)[-1])
    raise SystemExit("Gitleaks is required. Install Gitleaks.Gitleaks with winget.")


if __name__ == "__main__":
    raise SystemExit(subprocess.call([find_gitleaks(), *sys.argv[1:]]))

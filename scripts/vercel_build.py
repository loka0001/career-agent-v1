"""Build the SPA without mutating production infrastructure."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    install_command = "ci" if (ROOT / "web" / "package-lock.json").exists() else "install"
    # Vercel may restore a stale node_modules cache after package.json changes.
    # Always reconcile dependencies from the lockfile before the production build.
    run(npm, "--prefix", "web", install_command)
    run(npm, "--prefix", "web", "run", "build")
    public = ROOT / "public"
    public.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "web" / "dist", public, dirs_exist_ok=True)


if __name__ == "__main__":
    main()

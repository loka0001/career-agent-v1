from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_vercel_bundle_excludes_all_environment_files() -> None:
    patterns = {
        line.strip()
        for line in (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert ".env*" in patterns
    assert not any(pattern.startswith("!.env") for pattern in patterns)

from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_repository_handoff_manifest import build_manifest, validate_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "artifacts" / "production-readiness" / ("repository-handoff-manifest.json")


def test_current_repository_handoff_manifest_is_valid() -> None:
    document = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert validate_manifest(document, ROOT) == []


def test_repository_handoff_manifest_detects_stale_hash(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.write_text("print('first')\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, generated_at="2026-08-01T10:55:00+00:00")
    source.write_text("print('changed')\n", encoding="utf-8")

    assert "repository handoff manifest files is stale or invalid" in validate_manifest(
        manifest, tmp_path
    )


def test_repository_handoff_manifest_is_portable_between_checkout_paths(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "app.py").write_text("print('portable')\n", encoding="utf-8")
    manifest = build_manifest(source_root, generated_at="2026-09-01T00:00:00+00:00")
    (destination_root / "app.py").write_bytes(b"print('portable')\r\n")

    assert manifest["root"] == "."
    assert validate_manifest(manifest, destination_root) == []


def test_repository_handoff_manifest_rejects_excluded_file(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.write_text("print('first')\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, generated_at="2026-08-01T10:55:00+00:00")
    manifest["files"].append(
        {
            "path": ".env.local",
            "sha256": "0" * 64,
            "size_bytes": 12,
        }
    )

    assert "repository handoff manifest includes excluded path .env.local" in validate_manifest(
        manifest, tmp_path
    )


def test_repository_handoff_manifest_excludes_generated_coverage(tmp_path: Path) -> None:
    coverage = tmp_path / "web" / "coverage"
    coverage.mkdir(parents=True)
    (coverage / "index.html").write_text("volatile coverage output", encoding="utf-8")

    manifest = build_manifest(tmp_path, generated_at="2026-08-08T00:00:00+00:00")

    assert all(not item["path"].startswith("web/coverage/") for item in manifest["files"])


def test_repository_handoff_manifest_excludes_temporary_workspaces(tmp_path: Path) -> None:
    temporary = tmp_path / ".tmp" / "postgres-cluster"
    temporary.mkdir(parents=True)
    (temporary / "PG_VERSION").write_text("17\n", encoding="utf-8")

    manifest = build_manifest(tmp_path, generated_at="2026-09-05T00:00:00+00:00")

    assert all(not item["path"].startswith(".tmp/") for item in manifest["files"])


def test_repository_handoff_manifest_excludes_named_virtualenvs(tmp_path: Path) -> None:
    package = tmp_path / ".venv-win" / "Lib" / "site-packages"
    package.mkdir(parents=True)
    (package / "dependency.py").write_text("external = True\n", encoding="utf-8")

    manifest = build_manifest(tmp_path, generated_at="2026-09-13T00:00:00+00:00")

    assert all(not item["path"].startswith(".venv-win/") for item in manifest["files"])


def test_repository_handoff_manifest_excludes_downloaded_uv(tmp_path: Path) -> None:
    tool = tmp_path / "_uv" / "uv"
    tool.parent.mkdir()
    tool.write_bytes(b"downloaded executable")

    manifest = build_manifest(tmp_path, generated_at="2026-09-13T00:00:00+00:00")

    assert all(not item["path"].startswith("_uv/") for item in manifest["files"])


def test_repository_handoff_manifest_keeps_credential_named_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "app" / "services" / "credential_vault.py"
    source.parent.mkdir(parents=True)
    source.write_text("def encrypt_secret(value: str) -> str:\n    return value\n")
    exported_secrets = tmp_path / "provider-credentials.json"
    exported_secrets.write_text('{"token": "not-a-real-token"}\n', encoding="utf-8")

    manifest = build_manifest(tmp_path, generated_at="2026-09-06T00:00:00+00:00")
    paths = {item["path"] for item in manifest["files"]}

    assert "app/services/credential_vault.py" in paths
    assert "provider-credentials.json" not in paths


def test_repository_handoff_manifest_keeps_committed_seed_inputs(
    tmp_path: Path,
) -> None:
    seeds = tmp_path / "data" / "seeds"
    seeds.mkdir(parents=True)
    (seeds / "products.json").write_text("[]\n", encoding="utf-8")
    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir()
    (uploads / "merchant.txt").write_text("runtime data\n", encoding="utf-8")
    (tmp_path / "data" / "commerce.db").write_bytes(b"runtime database")

    manifest = build_manifest(tmp_path, generated_at="2026-09-06T00:00:00+00:00")
    paths = {item["path"] for item in manifest["files"]}

    assert "data/seeds/products.json" in paths
    assert "data/uploads/merchant.txt" not in paths
    assert "data/commerce.db" not in paths


def test_repository_handoff_manifest_detects_secret_like_content(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.write_text("print('first')\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, generated_at="2026-08-01T10:55:00+00:00")
    source.write_text("sk-" + "manifest1234567890abcdef\n", encoding="utf-8")

    findings = validate_manifest(manifest, tmp_path)

    assert any("app.py contains a secret-looking OpenAI key" in finding for finding in findings)

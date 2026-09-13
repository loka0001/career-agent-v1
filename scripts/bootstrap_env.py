"""Create a local .env with fresh secrets and a one-time demo password."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path

from app.security import hash_password

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password", help="Optional demo password (minimum 12 characters)")
    parser.add_argument("--force", action="store_true", help="Replace an existing .env")
    args = parser.parse_args()
    destination = ROOT / ".env"
    if destination.exists() and not args.force:
        raise SystemExit(".env already exists; use --force only if replacement is intended")
    password = args.password or secrets.token_urlsafe(14)
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    content = content.replace("DEMO_MODE=false", "DEMO_MODE=true", 1)
    content = content.replace("AI_PROVIDER=openai", "AI_PROVIDER=deterministic", 1)
    content = content.replace("DEMO_MERCHANT_EMAIL=", "DEMO_MERCHANT_EMAIL=merchant@example.com", 1)
    content = content.replace("ENABLE_FAKE_PUBLISHING=false", "ENABLE_FAKE_PUBLISHING=true", 1)
    content = content.replace("APP_SECRET_KEY=", f"APP_SECRET_KEY={secrets.token_urlsafe(48)}", 1)
    content = content.replace(
        "DEMO_MERCHANT_PASSWORD_HASH=",
        f"DEMO_MERCHANT_PASSWORD_HASH={hash_password(password)}",
        1,
    )
    destination.write_text(content, encoding="utf-8")
    print("Created .env")
    print("Demo email: merchant@example.com")
    print(f"Demo password (shown once): {password}")
    print("Access: free, no subscription checkout; order collection: cash on delivery")


if __name__ == "__main__":
    main()

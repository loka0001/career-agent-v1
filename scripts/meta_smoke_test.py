"""Explicit, non-publishing Meta credential check."""

from __future__ import annotations

import argparse

from app.config import get_settings
from app.integrations.facebook import RealFacebookPublisher
from app.integrations.instagram import RealInstagramPublisher


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-live-check",
        action="store_true",
        help="Confirm a live, read-only request to Meta",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.run_meta_smoke_tests:
        raise SystemExit("Set RUN_META_SMOKE_TESTS=true before a live credential check")
    if not args.confirm_live_check:
        raise SystemExit("Pass --confirm-live-check; this script never creates a post")
    RealFacebookPublisher(settings).check_connection()
    RealInstagramPublisher(settings).check_connection()
    print("Facebook Page and Instagram account credentials are readable. No post was created.")


if __name__ == "__main__":
    main()

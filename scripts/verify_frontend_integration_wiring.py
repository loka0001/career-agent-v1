"""Validate critical integration UI wiring that must not drift from backend contracts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    "app/api/routes/commerce.py": (
        'oauth_callback_router = APIRouter(prefix="/shopify/oauth"',
        '@oauth_callback_router.get("/callback")',
        "verify_shopify_oauth_callback(",
        '"shopify_code": code',
        '"shopify_state": state',
        '"shopify_shop": shop',
        '"shopify_hmac": hmac',
        '"shopify_timestamp": timestamp',
        'RedirectResponse(f"/app/integrations?{query}")',
    ),
    "app/main.py": ("application.include_router(commerce.oauth_callback_router)",),
    "app/services/commerce_connectors.py": (
        "def verify_shopify_oauth_callback(",
        'provider="shopify"',
        "OAuthTransactionRepository(session).validate(",
        'raise AuthenticationError("Shopify OAuth shop does not match state")',
    ),
    "web/src/lib/types.ts": (
        "export interface ShopifyOAuthStart",
        "authorization_url: string;",
        "state: string;",
        "shop: string;",
    ),
    "web/src/lib/api.ts": (
        "ShopifyOAuthStart,",
        "startShopifyOAuth:",
        '"/api/v1/integrations/commerce/shopify/oauth/start"',
        "exchangeShopifyOAuth:",
        '"/api/v1/integrations/commerce/shopify/oauth/exchange"',
    ),
    "web/src/features/integrations/CommerceConnections.tsx": (
        "handledShopifyOAuth",
        'query.get("shopify_code")',
        'query.get("shopify_state")',
        'query.get("shopify_shop")',
        'query.get("shopify_hmac")',
        'query.get("shopify_timestamp")',
        ".exchangeShopifyOAuth({ code, state, shop, hmac, timestamp, host })",
        "window.history.replaceState",
        "startShopifyOAuth",
        "window.location.assign(result.authorization_url)",
    ),
    "web/src/features/integrations/IntegrationsPage.tsx": (
        "async function loadConnections()",
        "api.integrations()",
        "api.providerConnections()",
        "setItems(integrationResponse.integrations)",
        "setConnections(connectionResponse)",
        "await loadConnections()",
    ),
}


def validate_frontend_integration_wiring(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    for relative, snippets in REQUIRED_SNIPPETS.items():
        path = root / relative
        if not path.is_file():
            findings.append(f"missing required integration wiring file: {relative}")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in content:
                findings.append(f"{relative} missing required integration wiring: {snippet}")
    return findings


def main() -> int:
    findings = validate_frontend_integration_wiring()
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Frontend integration wiring verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

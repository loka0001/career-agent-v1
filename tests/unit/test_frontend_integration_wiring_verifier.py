from __future__ import annotations

from pathlib import Path

from scripts.verify_frontend_integration_wiring import validate_frontend_integration_wiring


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_frontend_integration_wiring_verifier_accepts_required_contracts(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "app/api/routes/commerce.py",
        """
oauth_callback_router = APIRouter(prefix="/shopify/oauth", tags=["shopify-oauth"])
@oauth_callback_router.get("/callback")
def callback():
    verify_shopify_oauth_callback(
    values = {
        "shopify_code": code,
        "shopify_state": state,
        "shopify_shop": shop,
        "shopify_hmac": hmac,
        "shopify_timestamp": timestamp,
    }
    return RedirectResponse(f"/app/integrations?{query}")
""",
    )
    _write(
        tmp_path,
        "app/main.py",
        "application.include_router(commerce.oauth_callback_router)",
    )
    _write(
        tmp_path,
        "app/services/commerce_connectors.py",
        """
def verify_shopify_oauth_callback():
    provider="shopify"
    OAuthTransactionRepository(session).validate(
    raise AuthenticationError("Shopify OAuth shop does not match state")
""",
    )
    _write(
        tmp_path,
        "web/src/lib/types.ts",
        """
export interface ShopifyOAuthStart {
  authorization_url: string;
  state: string;
  shop: string;
}
""",
    )
    _write(
        tmp_path,
        "web/src/lib/api.ts",
        """
  ShopifyOAuthStart,
  startShopifyOAuth:
  "/api/v1/integrations/commerce/shopify/oauth/start"
  exchangeShopifyOAuth:
  "/api/v1/integrations/commerce/shopify/oauth/exchange"
""",
    )
    _write(
        tmp_path,
        "web/src/features/integrations/CommerceConnections.tsx",
        """
handledShopifyOAuth
query.get("shopify_code")
query.get("shopify_state")
query.get("shopify_shop")
query.get("shopify_hmac")
query.get("shopify_timestamp")
.exchangeShopifyOAuth({ code, state, shop, hmac, timestamp, host })
window.history.replaceState
startShopifyOAuth
window.location.assign(result.authorization_url)
""",
    )
    _write(
        tmp_path,
        "web/src/features/integrations/IntegrationsPage.tsx",
        """
async function loadConnections()
api.integrations()
api.providerConnections()
setItems(integrationResponse.integrations)
setConnections(connectionResponse)
await loadConnections()
""",
    )

    assert validate_frontend_integration_wiring(tmp_path) == []


def test_frontend_integration_wiring_verifier_rejects_missing_callback(
    tmp_path: Path,
) -> None:
    findings = validate_frontend_integration_wiring(tmp_path)

    assert "missing required integration wiring file: app/api/routes/commerce.py" in findings

"""OIDC-protected deployment of the SQLAlchemy STAC API."""

import os

from fastapi import Request, Response

from stac_fastapi.api.oidc import OIDCTokenAuth
from stac_fastapi.sqlalchemy.app import app


@app.get("/oauth2/introspect")
def token_rights(request: Request, response: Response) -> dict:
    """Show locally validated rights without claiming provider introspection."""
    response.headers["Cache-Control"] = "no-store"
    claims = request.state.auth
    fields = (
        "groups", "rights", "hiddenProductSlugs", "iss", "aud", "client_id",
        "azp", "sub", "sid", "iat", "exp", "scope",
    )
    return {
        **{name: claims[name] for name in fields if name in claims},
        "validation": "jwt",
        "active": True,
        "token_type": "Bearer",
        "rights": claims.get("rights", []),
        "hiddenProductSlugs": claims.get("hiddenProductSlugs", []),
        "allowed_products": sorted(request.scope["allowed_products"]),
    }


OIDCTokenAuth(
    issuer=os.environ["AUTH_ISSUER"],
    audience=os.environ["AUTH_AUDIENCE"],
    jwks_url=os.environ["AUTH_JWKS_URL"],
).install(app)

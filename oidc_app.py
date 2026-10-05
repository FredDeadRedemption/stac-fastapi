"""OIDC-protected deployment of the SQLAlchemy STAC API."""

import os

from stac_fastapi.api.oidc import OIDCTokenAuth
from stac_fastapi.sqlalchemy.app import app

OIDCTokenAuth(
    issuer=os.environ["AUTH_ISSUER"],
    audience=os.environ["AUTH_AUDIENCE"],
    jwks_url=os.environ["AUTH_JWKS_URL"],
).install(app)

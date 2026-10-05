# STAC API

## Optional OIDC authentication

Install `stac-fastapi.api[oidc]` and register authentication after all API routes:

```python
from stac_fastapi.api.oidc import OIDCTokenAuth

OIDCTokenAuth(issuer, audience, jwks_url).install(api.app)
```

An external OIDC provider must issue signed access tokens. The default algorithm
is EdDSA. Tokens require `exp`, `iat`, `iss`, `aud` and `sub`; signature, issuer,
audience and expiry are validated with 60 seconds of clock tolerance.
All API routes are protected except health (`/_mgmt/ping`, including prefixes)
and documentation/OpenAPI. Missing or invalid tokens return 401; unavailable
JWKS returns 503. Verified claims are available in `request.state.auth` and
`request.scope["auth"]`.

Product grants are `rights: ["product-<database product ID>"]`, minus
`hiddenProductSlugs`. Missing grants allow no products; malformed arrays return
403. `request.scope["allowed_products"]` supplies SQLAlchemy filtering before
pagination/counts; collection metadata remains visible. Mutations require
`stac-write`; `POST /search` remains a read. External asset URLs need their own
access controls. Login/PKCE belongs to the client and provider.

## Local deployment

With the sibling `kds-stac-fastapi-sqlalchemy` checkout, an external OIDC provider
and a database matching the backend models:

```shell
docker compose -f docker-compose.oidc.yml up -d --build
```

Requires Docker BuildKit additional contexts. Compose uses the standard
Dockerfile's optional `oidc` stage and serves `oidc_app:app` on port 8081.
Plain `docker build .` is unchanged. Configure these required settings in
Compose; missing or empty values fail startup:

| Setting | Meaning | Local default |
| --- | --- | --- |
| `AUTH_ISSUER` | Exact JWT `iss`, including scheme, host, path and trailing slash | `http://localhost:8180/realms/kds-example` |
| `AUTH_AUDIENCE` | Expected API `aud` string or array entry, not automatically the browser client ID | `dataforsyningen` |
| `AUTH_JWKS_URL` | Public signing-key endpoint reachable from the API container | `http://host.docker.internal:8180/realms/kds-example/protocol/openid-connect/certs` |

Issuer and JWKS hostnames may differ: issuer matches the token; JWKS fetches keys.
Configure the provider to include the API audience. Adjust provider and database
settings for your environment; Compose defaults are for local development.
Do not serve the backend's unauthenticated `stac_fastapi.sqlalchemy.app:app`
directly. The existing local database must match the backend schema; keep its
compatible image/adapter until any schema mismatch is resolved.

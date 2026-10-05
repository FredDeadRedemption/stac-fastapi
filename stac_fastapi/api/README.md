# STAC API

Install `stac-fastapi.api[oidc]` and apply
`OIDCTokenAuth(issuer, audience, jwks_url).install(api.app)` after registering
all routes. JWT validation uses EdDSA, requires `exp`, `iat`, `iss`, `aud`, `sub`,
and allows 60 seconds of clock tolerance. Invalid/missing tokens return 401;
unavailable JWKS returns 503. Health and documentation remain public.

The `oidc_app:app` deployment requires:

- `AUTH_ISSUER`: exact token `iss`, including scheme, host and path.
- `AUTH_AUDIENCE`: API audience in `aud`, not automatically the browser client ID.
- `AUTH_JWKS_URL`: signing-key endpoint reachable from the API container.

Missing/empty settings fail startup. Issuer and JWKS hostnames may differ.
Claims are available in `request.scope["auth"]` and `request.state.auth`.
Protected `GET /oauth2/introspect` shows available JWT claims, rights and effective
`allowed_products`. `validation: "jwt"` and `active: true` mean local validation
passed, not provider-confirmed revocation status; `token_type` is the Bearer scheme.
Product grants use `rights: ["product-<database product ID>"]` minus
`hiddenProductSlugs`; missing grants allow no products. Mutations require
`stac-write`; `POST /search` is a read. External asset URLs need separate protection.

With the sibling SQLAlchemy checkout, matching database schema and OIDC provider:

```shell
docker compose -f docker-compose.oidc.yml up -d --build
```

Compose selects the optional Dockerfile stage; the default build is unchanged.
Adjust its local provider/database settings. Use `oidc_app:app`, not the backend's
unauthenticated entrypoint. Keep the existing database's compatible image/adapter
until any schema mismatch is resolved.

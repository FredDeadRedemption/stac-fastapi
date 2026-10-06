Install `stac-fastapi.api[oidc]` and apply
`OIDCTokenAuth(issuer, audience, jwks_url).install(api.app)` to enable OIDC.

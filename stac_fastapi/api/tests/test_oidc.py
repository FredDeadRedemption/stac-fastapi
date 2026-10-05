import time
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from stac_fastapi.api.oidc import OIDCTokenAuth
from test_api import TestRouteDependencies as RouteDependencies


@pytest.fixture
def authenticated_app(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    auth = OIDCTokenAuth("https://issuer.example", "stac", "https://issuer.example/jwks")
    monkeypatch.setattr(
        auth.jwks,
        "get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key=private_key.public_key()),
    )
    app = FastAPI()

    @app.api_route("/data", methods=["GET", "POST", "PUT", "DELETE"])
    def data(request: Request):
        assert request.scope["auth"] == request.state.auth
        return {
            "sub": request.state.auth["sub"],
            "products": sorted(request.scope["allowed_products"]),
        }

    @app.get("/_mgmt/ping")
    def ping():
        return {"message": "PONG"}

    auth.install(app)
    auth.install(app)
    return app, auth, private_key


def token(private_key, **overrides):
    now = int(time.time())
    claims = {
        "iss": "https://issuer.example",
        "aud": "stac",
        "sub": "demo-user",
        "iat": now,
        "exp": now + 300,
        "rights": ["product-skraafoto_fri", "stac-write"],
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="EdDSA")


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_missing_token_and_valid_token(authenticated_app, method):
    app, _, key = authenticated_app
    with TestClient(app) as client:
        response = client.request(method, "/data")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        response = client.request(
            method, "/data", headers={"Authorization": f"Bearer {token(key)}"}
        )
        assert response.status_code == 200
        assert response.json() == {"sub": "demo-user", "products": ["skraafoto_fri"]}
    data_route = next(route for route in app.routes if route.path == "/data")
    assert len(data_route.dependencies) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://wrong.example"},
        {"aud": "wrong"},
        {"exp": 1},
        {"iat": int(time.time()) + 3600},
    ],
)
def test_invalid_claims(authenticated_app, overrides):
    app, _, key = authenticated_app
    with TestClient(app) as client:
        response = client.get(
            "/data", headers={"Authorization": f"Bearer {token(key, **overrides)}"}
        )
        assert response.status_code == 401


@pytest.mark.parametrize("claim", ["iss", "aud", "sub", "iat", "exp"])
def test_required_claims(authenticated_app, claim):
    app, _, key = authenticated_app
    claims = jwt.decode(token(key), options={"verify_signature": False})
    del claims[claim]
    encoded = jwt.encode(claims, key, algorithm="EdDSA")
    with TestClient(app) as client:
        assert client.get(
            "/data", headers={"Authorization": f"Bearer {encoded}"}
        ).status_code == 401


@pytest.mark.parametrize("authorization", ["Basic abc", "Bearer", "Bearer malformed"])
def test_malformed_credentials(authenticated_app, authorization):
    app, _, _ = authenticated_app
    with TestClient(app) as client:
        assert client.get(
            "/data", headers={"Authorization": authorization}
        ).status_code == 401


def test_invalid_signature(authenticated_app):
    app, _, _ = authenticated_app
    other_key = Ed25519PrivateKey.generate()
    with TestClient(app) as client:
        assert client.get(
            "/data", headers={"Authorization": f"Bearer {token(other_key)}"}
        ).status_code == 401


def test_disallowed_algorithm(authenticated_app):
    app, _, _ = authenticated_app
    encoded = jwt.encode({"sub": "demo-user"}, "not-an-allowed-key", algorithm="HS256")
    with TestClient(app) as client:
        assert client.get(
            "/data", headers={"Authorization": f"Bearer {encoded}"}
        ).status_code == 401


@pytest.mark.parametrize(
    "error,status",
    [
        (jwt.PyJWKClientConnectionError("unavailable"), 503),
        (jwt.PyJWKClientError("unknown kid"), 401),
    ],
)
def test_jwks_failures(authenticated_app, monkeypatch, error, status):
    app, auth, key = authenticated_app

    def fail(token):
        raise error

    monkeypatch.setattr(auth.jwks, "get_signing_key_from_jwt", fail)
    with TestClient(app) as client:
        assert client.get(
            "/data", headers={"Authorization": f"Bearer {token(key)}"}
        ).status_code == status


def test_public_routes_and_openapi(authenticated_app):
    app, _, _ = authenticated_app
    with TestClient(app) as client:
        for path in ["/_mgmt/ping", "/docs", "/openapi.json"]:
            assert client.get(path).status_code == 200
        schema = client.get("/openapi.json").json()
        assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
        for method in ["get", "post", "put", "delete"]:
            assert schema["paths"]["/data"][method]["security"] == [{"HTTPBearer": []}]


def test_stac_extension_routes_are_protected():
    api = RouteDependencies._build_api()
    auth = OIDCTokenAuth("https://issuer.example", "stac", "https://issuer.example/jwks")
    auth.install(api.app)
    with TestClient(api.app) as client:
        for method, path in [
            ("GET", "/"),
            ("GET", "/collections"),
            ("POST", "/search"),
            ("POST", "/collections"),
            ("DELETE", "/collections/demo"),
            ("POST", "/collections/demo/items"),
        ]:
            assert client.request(method, path).status_code == 401
        assert client.get("/_mgmt/ping").status_code == 200


def test_explicit_public_paths_and_late_routes(authenticated_app):
    app, _, _ = authenticated_app
    auth = OIDCTokenAuth("https://issuer.example", "stac", "https://issuer.example/jwks")

    @app.get("/public")
    def public():
        return {}

    @app.get("/late")
    def late():
        return {}

    auth.install(app, public_paths=["/public"])
    with TestClient(app) as client:
        assert client.get("/public").status_code == 200
        assert client.get("/late").status_code == 401


def test_prefixed_health_route_is_public():
    app = FastAPI()
    app.state.router_prefix = "/stac"

    @app.get("/stac/_mgmt/ping")
    def ping():
        return {}

    @app.get("/stac/collections")
    def collections():
        return {}

    OIDCTokenAuth("https://issuer.example", "stac", "https://issuer.example/jwks").install(app)
    with TestClient(app) as client:
        assert client.get("/stac/_mgmt/ping").status_code == 200
        assert client.get("/stac/collections").status_code == 401


def test_deployment_entrypoint_enables_authentication(monkeypatch):
    api = RouteDependencies._build_api()
    monkeypatch.setitem(
        sys.modules, "stac_fastapi.sqlalchemy.app", SimpleNamespace(app=api.app)
    )
    monkeypatch.setenv("AUTH_ISSUER", "https://issuer.example")
    monkeypatch.setenv("AUTH_AUDIENCE", "stac")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://issuer.example/jwks")
    deployed = runpy.run_path(str(Path(__file__).resolve().parents[3] / "oidc_app.py"))
    assert deployed["app"] is api.app
    with TestClient(api.app) as client:
        assert client.get("/collections").status_code == 401
        assert client.post("/collections").status_code == 401
        assert client.get("/_mgmt/ping").status_code == 200


@pytest.mark.parametrize("missing", ["AUTH_ISSUER", "AUTH_AUDIENCE", "AUTH_JWKS_URL"])
def test_deployment_requires_configuration(monkeypatch, missing):
    monkeypatch.setitem(
        sys.modules, "stac_fastapi.sqlalchemy.app", SimpleNamespace(app=FastAPI())
    )
    for name in ("AUTH_ISSUER", "AUTH_AUDIENCE", "AUTH_JWKS_URL"):
        monkeypatch.setenv(name, "configured")
    monkeypatch.delenv(missing)
    with pytest.raises(KeyError, match=missing):
        runpy.run_path(str(Path(__file__).resolve().parents[3] / "oidc_app.py"))


@pytest.mark.parametrize(
    "claims, status, products",
    [
        ({"rights": []}, 200, []),
        ({"hiddenProductSlugs": ["skraafoto_fri"]}, 200, []),
        ({"rights": ["product-skraafoto_hemmelig"]}, 200, ["skraafoto_hemmelig"]),
        ({"rights": "product-skraafoto_fri"}, 403, None),
        ({"hiddenProductSlugs": None}, 403, None),
        ({"rights": [123]}, 403, None),
    ],
)
def test_product_entitlements(authenticated_app, claims, status, products):
    app, _, key = authenticated_app
    with TestClient(app) as client:
        response = client.get(
            "/data", headers={"Authorization": f"Bearer {token(key, **claims)}"}
        )
        assert response.status_code == status
        if status == 200:
            assert response.json()["products"] == products


def test_product_access_does_not_grant_writes(authenticated_app):
    app, _, key = authenticated_app
    with TestClient(app) as client:
        response = client.delete(
            "/data",
            headers={"Authorization": f"Bearer {token(key, rights=['product-skraafoto_fri'])}"},
        )
        assert response.status_code == 403

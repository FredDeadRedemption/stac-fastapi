<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <img src="https://github.com/radiantearth/stac-site/raw/master/images/logo/stac-030-long.png" width=400>
  <p align="center">FastAPI implemention of the STAC API spec.</p>
</p>
<p align="center">
  <a href="https://github.com/stac-utils/stac-fastapi/actions?query=workflow%3Acicd" target="_blank">
      <img src="https://github.com/stac-utils/stac-fastapi/workflows/stac-fastapi/badge.svg" alt="Test">
  </a>
  <a href="https://pypi.org/project/stac-fastapi" target="_blank">
      <img src="https://img.shields.io/pypi/v/stac-fastapi.api?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://github.com/stac-utils/stac-fastapi/blob/main/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/stac-utils/stac-fastapi.svg" alt="License">
  </a>
</p>

---

**Documentation**: [https://stac-utils.github.io/stac-fastapi/](https://stac-utils.github.io/stac-fastapi/)

**Source Code**: [https://github.com/stac-utils/stac-fastapi](https://github.com/stac-utils/stac-fastapi)

---

Python library for building a STAC compliant FastAPI application.  The project is split up into several namespace
packages:

- **stac_fastapi.api**: An API layer which enforces the [stac-api-spec](https://github.com/radiantearth/stac-api-spec).
- **stac_fastapi.extensions**: Abstract base classes for [STAC API extensions](https://github.com/radiantearth/stac-api-spec/blob/master/extensions.md) and third-party extensions.
- **stac_fastapi.types**: Shared types and abstract base classes used by the library.

#### Backends

Backends are hosted in their own repositories:

- [stac-fastapi-pgstac](https://github.com/stac-utils/stac-fastapi-pgstac): Postgres backend implementation with [PgSTAC](https://github.com/stac-utils/pgstac).
- [stac-fastapi-sqlalchemy](https://github.com/stac-utils/stac-fastapi-sqlalchemy): Postgres backend implementation with [sqlalchemy](https://www.sqlalchemy.org/).
- [stac-fastapi-elasticsearch](https://github.com/stac-utils/stac-fastapi-elasticsearch): Backend implementation with [Elasticsearch](https://github.com/elastic/elasticsearch).

`stac-fastapi` was initially developed by [arturo-ai](https://github.com/arturo-ai).

## Installation

```bash
# Install from PyPI
python -m pip install stac-fastapi.types stac-fastapi.api stac-fastapi.extensions

# Install a backend of your choice
python -m pip install stac-fastapi.sqlalchemy
# or
python -m pip install stac-fastapi.pgstac
```

Other backends may be available from other sources, search [PyPI](https://pypi.org/) for more.

## Development

Install the packages in editable mode:

```shell
python -m pip install -e \
  'stac_fastapi/types[dev]' \
  'stac_fastapi/api[dev]' \
  'stac_fastapi/extensions[dev]'
```

To run the tests:

```shell
python -m pytest
```

## Atlas

This branch carries the Atlas version. The main difference from upstream is JWT based access control: an optional OIDC layer (`stac_fastapi.api.oidc`) protects every API route except the ping endpoint. A credential arrives as a `Authorization: Bearer` header, a `token` header, or a `token` query parameter. JWTs are verified in-process against the issuer's JWKS; opaque API keys are introspected over RFC 7662 behind a short-lived decision cache. The product entitlements in the token claims decide which products the request can see, exposed to the backend as `request.scope["allowed_products"]`.

"""API-key auth for the write path and the schema docs.

This module is complete and working. It is deliberately **not wired up** — the
enforcement lines are commented out in `app/main.py` and `app/routers/items.py`
so the endpoints stay open for anyone who wants to poke at them.

To turn it on: set `API_KEY` in the environment and uncomment the two
`dependencies=[Depends(require_api_key)]` lines.

For an actual AWS deployment, a shared secret is the fallback, not the first
choice. Preferred, in order:

1. **Lambda Function URL with `AWS_IAM`** — callers sign requests with SigV4
   against an IAM role. The service stores no credential at all.
2. **API Gateway usage plans** — key issuance, rotation, and per-client
   throttling handled outside the application.
3. This module — when the caller can't sign requests.
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Depends(api_key_header)) -> None:
    expected = settings.api_key

    if not expected:
        # Fail closed: auth was switched on but nothing was configured.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "API key auth is enabled but no API_KEY is configured",
        )

    # compare_digest, not ==, so the comparison time doesn't leak the prefix.
    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

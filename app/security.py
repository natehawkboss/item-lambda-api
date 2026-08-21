"""API-key auth for the write path.

Wired up live on `POST /items` — see `app/routers/items.py`. Enforcement is
driven by configuration rather than by editing code: set `API_KEY` in the
environment and writes require a matching `X-API-Key` header.

This demo deployment leaves `API_KEY` unset so the write path stays open for
anyone who wants to try it. That is a deliberate demo choice, not a default I
would ship: a real deployment sets the key (or, better, drops this module for
`AWS_IAM` on a Function URL or an API Gateway usage plan, where callers sign
requests with SigV4 and the service stores no credential at all).
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Depends(api_key_header)) -> None:
    expected = settings.api_key

    if not expected:
        return  # unconfigured: demo mode, writes are open

    # compare_digest, not ==, so comparison time doesn't leak the prefix.
    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

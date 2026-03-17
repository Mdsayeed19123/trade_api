"""
Authentication helpers.

Strategy chosen: **Guest JWT**
- No credentials needed; anyone can hit POST /auth/guest-token and get a
  short-lived bearer token.
- Simple to evaluate, but still forces all analysis calls to be authenticated.
- Production upgrade path: swap create_guest_token for a real user-db lookup.
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple

import jwt
from fastapi import HTTPException

from config import settings


def create_guest_token(client_ip: str = "unknown") -> Tuple[str, str]:
    """
    Create a signed JWT for guest access.

    Returns
    -------
    token : str
        Signed JWT string.
    expires_at : str
        ISO-8601 expiry timestamp (UTC).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": f"guest@{client_ip}",
        "role": "guest",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire.isoformat()


def verify_token(token: str) -> dict:
    """
    Decode and validate a JWT.  Raises HTTP 401 on any failure.

    Returns
    -------
    payload : dict
        Decoded token claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Request a new one at POST /auth/guest-token.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

from fastapi import Header, HTTPException
from jose import JWTError, jwt
from pydantic import ValidationError
from app.config import settings
from app.models.auth import TokenClaims
from typing import Optional


def decode_token(authorization: Optional[str] = Header(default=None)) -> TokenClaims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims.model_validate(payload)
    except (JWTError, ValidationError):
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None

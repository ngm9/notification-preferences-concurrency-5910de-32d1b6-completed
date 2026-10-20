from uuid import UUID

from fastapi import Depends, HTTPException

from app.middleware.auth import decode_token
from app.models.auth import TokenClaims
from app.policies.preferences import (
    PreferencesAccessDenied,
    authorize_tenant_access,
    authorize_user_access,
)
from app.repositories.preferences_repository import get_user_tenant_id


def authorize_preferences_access(
    user_id: UUID,
    claims: TokenClaims = Depends(decode_token),
) -> TokenClaims:
    caller_tenant_id = get_user_tenant_id(claims.user_id)
    if caller_tenant_id is None:
        raise HTTPException(status_code=403, detail="Your account is not authorized.")

    try:
        authorize_tenant_access(claims.tenant_id, caller_tenant_id)
        authorize_user_access(claims, user_id)
    except PreferencesAccessDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    target_tenant_id = get_user_tenant_id(user_id)
    if target_tenant_id is None:
        raise HTTPException(status_code=404, detail="Preferences not found.")

    try:
        authorize_tenant_access(claims.tenant_id, target_tenant_id)
    except PreferencesAccessDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    return claims

import re
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from app.dependencies.preferences import authorize_preferences_access
from app.models.auth import TokenClaims
from app.models.preferences import PreferencesUpdateRequest, PreferencesResponse
from app.services.preferences_service import (
    PreferencesNotFound,
    PreferencesVersionConflict,
    apply_preference_updates,
    fetch_user_preferences,
)

router = APIRouter()


def _parse_if_match(if_match: str) -> int:
    match = re.fullmatch(r'"([1-9][0-9]*)"', if_match.strip())
    if match is None:
        raise HTTPException(
            status_code=400,
            detail='If-Match must contain one strong version ETag, such as "1".',
        )
    return int(match.group(1))


def _raise_http_error(error: Exception) -> NoReturn:
    if isinstance(error, PreferencesNotFound):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, PreferencesVersionConflict):
        raise HTTPException(status_code=412, detail=str(error)) from error
    raise error


@router.get("/users/{user_id}/preferences", response_model=PreferencesResponse)
def get_preferences(
    user_id: UUID,
    response: Response,
    claims: TokenClaims = Depends(authorize_preferences_access),
):
    try:
        prefs = fetch_user_preferences(user_id, claims.tenant_id)
    except PreferencesNotFound as error:
        _raise_http_error(error)
    response.headers["ETag"] = f'"{prefs.version}"'
    return PreferencesResponse(**prefs.model_dump())


@router.put("/users/{user_id}/preferences", response_model=PreferencesResponse)
def update_preferences(
    user_id: UUID,
    body: PreferencesUpdateRequest,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    claims: TokenClaims = Depends(authorize_preferences_access),
):
    if if_match is None:
        raise HTTPException(
            status_code=428,
            detail="If-Match header is required; fetch the current preferences ETag before updating.",
        )

    expected_version = _parse_if_match(if_match)
    try:
        updated = apply_preference_updates(
            user_id,
            body,
            claims.tenant_id,
            expected_version,
        )
    except (
        PreferencesNotFound,
        PreferencesVersionConflict,
    ) as error:
        _raise_http_error(error)
    response.headers["ETag"] = f'"{updated.version}"'
    return PreferencesResponse(**updated.model_dump())

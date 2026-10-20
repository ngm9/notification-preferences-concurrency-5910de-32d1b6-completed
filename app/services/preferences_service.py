from uuid import UUID
from app.models.preferences import NotificationPreferences, PreferencesUpdateRequest
from app.repositories.preferences_repository import (
    get_preferences_by_user,
    update_preferences,
)


class PreferencesNotFound(Exception):
    pass


class PreferencesVersionConflict(Exception):
    pass


def fetch_user_preferences(
    user_id: UUID,
    tenant_id: UUID,
) -> NotificationPreferences:
    preferences = get_preferences_by_user(user_id, tenant_id)
    if preferences is None:
        raise PreferencesNotFound("Preferences not found.")
    return preferences


def apply_preference_updates(
    user_id: UUID,
    request: PreferencesUpdateRequest,
    tenant_id: UUID,
    expected_version: int,
) -> NotificationPreferences:
    updates = request.model_dump(exclude_none=True)
    status, updated = update_preferences(
        user_id,
        tenant_id,
        expected_version,
        updates,
    )
    if status == "updated" and updated is not None:
        return updated
    if status == "not_found":
        raise PreferencesNotFound("Preferences not found.")
    raise PreferencesVersionConflict(
        "Preferences changed since they were read; fetch the latest ETag and retry."
    )

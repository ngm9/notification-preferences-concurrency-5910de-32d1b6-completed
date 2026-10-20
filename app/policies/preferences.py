from uuid import UUID

from app.models.auth import TokenClaims


class PreferencesAccessDenied(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def authorize_user_access(claims: TokenClaims, target_user_id: UUID) -> None:
    if claims.user_id != target_user_id and claims.role != "admin":
        raise PreferencesAccessDenied("You may only access your own preferences.")


def authorize_tenant_access(
    caller_tenant_id: UUID,
    target_tenant_id: UUID,
) -> None:
    if caller_tenant_id != target_tenant_id:
        raise PreferencesAccessDenied(
            "You may not access preferences outside your tenant."
        )

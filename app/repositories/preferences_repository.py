from uuid import UUID
from typing import Literal, Optional
from app.database import get_db
from app.models.preferences import NotificationPreferences


def get_user_tenant_id(user_id: UUID) -> Optional[UUID]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tenant_id FROM users WHERE id = %s",
                (str(user_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return UUID(row["tenant_id"])


def get_preferences_by_user(
    user_id: UUID,
    tenant_id: UUID,
) -> Optional[NotificationPreferences]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, tenant_id, email_enabled, sms_enabled, push_enabled, frequency, version "
                "FROM notification_preferences WHERE user_id = %s AND tenant_id = %s",
                (str(user_id), str(tenant_id)),
            )
            row = cur.fetchone()
            if not row:
                return None
            return NotificationPreferences(**row)


def update_preferences(
    user_id: UUID,
    tenant_id: UUID,
    expected_version: int,
    updates: dict,
) -> tuple[Literal["updated", "conflict", "not_found"], Optional[NotificationPreferences]]:
    allowed_fields = ("email_enabled", "sms_enabled", "push_enabled", "frequency")
    unexpected_fields = set(updates) - set(allowed_fields)
    if unexpected_fields:
        raise ValueError(f"Unsupported preference fields: {sorted(unexpected_fields)}")

    set_clauses = [f"{key} = %s" for key in allowed_fields if key in updates]
    values = [updates[key] for key in allowed_fields if key in updates]
    set_clauses.extend(
        ("version = notification_preferences.version + 1", "updated_at = NOW()")
    )

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "WITH target AS MATERIALIZED ("
                "  SELECT user_id, tenant_id, version "
                "  FROM notification_preferences "
                "  WHERE user_id = %s AND tenant_id = %s "
                "  FOR UPDATE"
                "), updated AS ("
                f"  UPDATE notification_preferences SET {', '.join(set_clauses)} "
                "  FROM target "
                "  WHERE notification_preferences.user_id = target.user_id "
                "    AND notification_preferences.tenant_id = target.tenant_id "
                "    AND target.version = %s "
                "  RETURNING notification_preferences.user_id, "
                "notification_preferences.tenant_id, "
                "notification_preferences.email_enabled, "
                "notification_preferences.sms_enabled, "
                "notification_preferences.push_enabled, "
                "notification_preferences.frequency, "
                "notification_preferences.version"
                ") "
                "SELECT 'updated' AS status, to_jsonb(updated) AS preference "
                "FROM updated "
                "UNION ALL "
                "SELECT 'conflict', NULL::jsonb FROM target WHERE version <> %s "
                "UNION ALL "
                "SELECT 'not_found', NULL::jsonb "
                "WHERE NOT EXISTS (SELECT 1 FROM target)",
                [str(user_id), str(tenant_id)]
                + values
                + [expected_version, expected_version],
            )
            row = cur.fetchone()
            status = row["status"]
            preference = (
                NotificationPreferences(**row["preference"])
                if row["preference"] is not None
                else None
            )
            return status, preference

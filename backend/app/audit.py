from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy.orm import Session

from .entities import AuditEventRecord


def record_event(
    session: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str = "",
) -> AuditEventRecord:
    event = AuditEventRecord(
        id=f"audit_{secrets.token_hex(10)}",
        actor=actor or "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before or {},
        after=after or {},
        metadata_json=metadata or {},
        request_id=request_id,
    )
    session.add(event)
    return event

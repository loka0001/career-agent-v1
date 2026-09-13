"""Audit trail for human approval and external actions."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditEventModel


class AuditRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(
        self,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
        organization_id: str | None = None,
        store_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> None:
        self._session.add(
            AuditEventModel(
                actor=actor,
                organization_id=organization_id,
                store_id=store_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_json=metadata or {},
            )
        )
        self._session.flush()

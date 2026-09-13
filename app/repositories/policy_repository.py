"""Store policies with stable citations."""

from __future__ import annotations

import builtins

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PolicyModel
from app.domain.models import PolicyExcerpt


class PolicyRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, store_id: str) -> list[PolicyExcerpt]:
        rows = self._session.scalars(
            select(PolicyModel)
            .where(PolicyModel.store_id == store_id)
            .order_by(PolicyModel.source_ref)
        ).all()
        return [
            PolicyExcerpt(source_ref=row.source_ref, title=row.title, body=row.body, score=1.0)
            for row in rows
        ]

    def rows(self, store_id: str) -> builtins.list[PolicyModel]:
        return list(
            self._session.scalars(select(PolicyModel).where(PolicyModel.store_id == store_id))
        )

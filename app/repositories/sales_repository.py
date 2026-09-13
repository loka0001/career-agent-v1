"""Minimal, non-PII sales query audit storage."""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.db.models import SalesQueryModel
from app.domain.models import SalesAssistantResponse


class SalesQueryRepository:
    def __init__(self, session: Session):
        self._session = session

    def save(self, store_id: str, message: str, response: SalesAssistantResponse) -> None:
        message_digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
        response_digest = hashlib.sha256(response.reply.encode("utf-8")).hexdigest()
        self._session.add(
            SalesQueryModel(
                store_id=store_id,
                message=f"sha256:{message_digest}",
                parsed_need_json=response.need.model_dump(mode="json"),
                recommended_product_ids_json=[item.product_id for item in response.recommendations],
                response_text=f"sha256:{response_digest}",
                citations_json=response.citations,
            )
        )
        self._session.flush()

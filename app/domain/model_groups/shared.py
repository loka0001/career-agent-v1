"""Generated shared slice of models.py."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, from_attributes=True)


class MoneyModel(ContractModel):
    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return format(value, "f")
        return value

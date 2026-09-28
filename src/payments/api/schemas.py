from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from payments.domain.transaction import CURRENCIES


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str
    country: str

    @field_validator("currency")
    @classmethod
    def known_currency(cls, value: str) -> str:
        value = value.upper()
        if value not in CURRENCIES:
            raise ValueError(f"unsupported currency: {value}")
        return value

    @field_validator("country")
    @classmethod
    def alpha_2(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError(f"country must be an ISO 3166-1 alpha-2 code, got {value!r}")
        return value


class TransactionResponse(BaseModel):
    transaction_id: str
    customer_id: str
    amount: Decimal
    currency: str
    country: str
    status: str
    decision_reason: str | None
    created_at: datetime
    processed_at: datetime | None

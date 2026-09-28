from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from functools import cache

import boto3
from fastapi import FastAPI, HTTPException

from payments.api.schemas import TransactionRequest, TransactionResponse
from payments.db.engine import session_scope
from payments.db.repository import fetch, insert_pending
from payments.domain.fraud import Status

app = FastAPI(title="payments", version="1.0.0")


@cache
def get_sqs():
    return boto3.client("sqs")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transactions", status_code=202, response_model=TransactionResponse)
def submit(request: TransactionRequest) -> TransactionResponse:
    transaction_id = f"tx-{uuid.uuid4().hex[:16]}"
    created_at = datetime.now(UTC)

    with session_scope() as session:
        insert_pending(
            session,
            transaction_id=transaction_id,
            customer_id=request.customer_id,
            amount=request.amount,
            currency=request.currency,
            country=request.country,
            created_at=created_at,
        )

    get_sqs().send_message(
        QueueUrl=os.environ["QUEUE_URL"],
        MessageBody=json.dumps(
            {
                "transaction_id": transaction_id,
                "customer_id": request.customer_id,
                "amount": str(request.amount),
                "currency": request.currency,
                "country": request.country,
                "created_at": created_at.isoformat(),
            }
        ),
    )

    return TransactionResponse(
        transaction_id=transaction_id,
        customer_id=request.customer_id,
        amount=request.amount,
        currency=request.currency,
        country=request.country,
        status=Status.PENDING.value,
        decision_reason=None,
        created_at=created_at,
        processed_at=None,
    )


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get(transaction_id: str) -> TransactionResponse:
    with session_scope() as session:
        record = fetch(session, transaction_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"no transaction {transaction_id}")
        return TransactionResponse.model_validate(record, from_attributes=True)

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from payments.db.models import TransactionRecord
from payments.domain.fraud import Decision
from payments.domain.transaction import Transaction


def count_recent(session: Session, transaction: Transaction, window: timedelta) -> int:
    statement = (
        select(func.count())
        .select_from(TransactionRecord)
        .where(
            TransactionRecord.customer_id == transaction.customer_id,
            TransactionRecord.transaction_id != transaction.transaction_id,
            TransactionRecord.created_at > transaction.created_at - window,
            TransactionRecord.created_at <= transaction.created_at,
        )
    )
    return session.scalar(statement) or 0


def record_decision(session: Session, transaction: Transaction, decision: Decision) -> None:
    decided_at = datetime.now(UTC)
    statement = insert(TransactionRecord).values(
        transaction_id=transaction.transaction_id,
        customer_id=transaction.customer_id,
        amount=transaction.amount,
        currency=transaction.currency,
        country=transaction.country,
        status=decision.status.value,
        decision_reason=decision.reason,
        created_at=transaction.created_at,
        processed_at=decided_at,
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[TransactionRecord.transaction_id],
            set_={
                "status": decision.status.value,
                "decision_reason": decision.reason,
                "processed_at": decided_at,
            },
        )
    )

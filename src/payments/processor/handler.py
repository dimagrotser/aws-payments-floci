from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from payments.db.engine import session_scope
from payments.db.repository import count_recent, record_decision
from payments.domain.config import rules_from_env
from payments.domain.fraud import CustomerHistory, Rules, evaluate
from payments.domain.transaction import parse_transaction

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    rules = rules_from_env()

    failures = []
    for record in event.get("Records", []):
        try:
            with session_scope() as session:
                outcome = process(record["body"], rules, session)
            logger.info("decided %s", outcome)
        except Exception:
            logger.exception("message %s failed", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def process(body: str, rules: Rules, session: Session) -> str:
    transaction = parse_transaction(body)

    window = timedelta(minutes=rules.velocity_window_minutes)
    history = CustomerHistory(recent_transactions=count_recent(session, transaction, window))

    decision = evaluate(transaction, history, rules)
    record_decision(session, transaction, decision)

    return f"{transaction.transaction_id} {decision.status.value} ({decision.reason})"

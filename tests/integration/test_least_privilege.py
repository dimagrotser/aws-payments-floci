"""Checked against the deployed role, not against the .tf file.

Floci evaluates IAM for real, so `simulate-principal-policy` answers the same question
the emulator would answer at request time. Widen the policy and these tests go red.
"""

import pytest

pytestmark = pytest.mark.integration

ROLE = "arn:aws:iam::000000000000:role/payments-processor-role"


@pytest.fixture(scope="module")
def simulate(iam):
    def _simulate(action: str, resource: str) -> str:
        results = iam.simulate_principal_policy(
            PolicySourceArn=ROLE, ActionNames=[action], ResourceArns=[resource]
        )["EvaluationResults"]
        return results[0]["EvalDecision"]

    return _simulate


def test_it_may_write_its_own_decisions(simulate, outputs):
    decision = simulate("s3:PutObject", f"arn:aws:s3:::{outputs['bucket']}/decisions/tx-1.json")

    assert decision == "allowed"


def test_it_may_not_write_anywhere_else_in_the_bucket(simulate, outputs):
    # The reports prefix belongs to the reporter, which arrives in stage 4.
    decision = simulate("s3:PutObject", f"arn:aws:s3:::{outputs['bucket']}/reports/2026-09-29.csv")

    assert decision != "allowed"


@pytest.mark.parametrize("action", ["s3:GetObject", "s3:DeleteObject", "s3:ListBucket"])
def test_it_may_only_write_to_s3(simulate, outputs, action):
    decision = simulate(action, f"arn:aws:s3:::{outputs['bucket']}/decisions/tx-1.json")

    assert decision != "allowed"


def test_it_may_consume_its_queue(simulate, queue_arn):
    assert simulate("sqs:ReceiveMessage", queue_arn) == "allowed"
    assert simulate("sqs:DeleteMessage", queue_arn) == "allowed"


def test_it_may_not_publish_to_its_own_queue(simulate, queue_arn):
    # Producing transactions is the API's job; the processor only consumes.
    assert simulate("sqs:SendMessage", queue_arn) != "allowed"


def test_it_may_not_touch_the_dead_letter_queue(simulate, queue_arn):
    dlq_arn = f"{queue_arn}-dlq"

    assert simulate("sqs:ReceiveMessage", dlq_arn) != "allowed"
    assert simulate("sqs:DeleteMessage", dlq_arn) != "allowed"

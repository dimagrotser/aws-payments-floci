import pytest

pytestmark = pytest.mark.integration

ROLE = "arn:aws:iam::000000000000:role/payments-processor-role"


@pytest.fixture(scope="module")
def simulate(iam):
    # Floci evaluates IAM for real, so the simulator answers the same question the
    # emulator would answer at request time.
    def _simulate(action: str, resource: str) -> str:
        results = iam.simulate_principal_policy(
            PolicySourceArn=ROLE, ActionNames=[action], ResourceArns=[resource]
        )["EvaluationResults"]
        return results[0]["EvalDecision"]

    return _simulate


def test_it_may_read_the_database_credentials(simulate, outputs):
    assert simulate("secretsmanager:GetSecretValue", outputs["db_secret_arn"]) == "allowed"


@pytest.mark.parametrize(
    "action",
    ["secretsmanager:PutSecretValue", "secretsmanager:DeleteSecret", "secretsmanager:UpdateSecret"],
)
def test_it_may_only_read_that_secret(simulate, outputs, action):
    assert simulate(action, outputs["db_secret_arn"]) != "allowed"


def test_it_has_no_business_in_the_bucket(simulate, outputs):
    # Nothing writes to the bucket until the reporter arrives in stage 4.
    bucket = f"arn:aws:s3:::{outputs['bucket']}"

    assert simulate("s3:PutObject", f"{bucket}/reports/2026-09-29.csv") != "allowed"
    assert simulate("s3:GetObject", f"{bucket}/reports/2026-09-29.csv") != "allowed"


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

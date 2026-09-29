# aws-payments-floci

A transaction processing system shaped the way you would actually build one on AWS: an API
on ECS writes to RDS and publishes to SQS, a Lambda applies anti-fraud rules and settles the
status, failed messages end up in a DLQ, and a scheduled Lambda drops a daily CSV on S3.
All of it is Terraform. None of it needs an AWS account, because it runs on
[Floci](https://floci.io), a local emulator.

> **Status: work in progress.** Stage 4 is done, which means the whole architecture is
> in place: the API on ECS accepts a transaction and publishes it, a Lambda settles it
> against the anti-fraud rules, messages nobody can parse land in the dead letter queue,
> and a scheduled Lambda writes the day's transactions to S3 as CSV. What is left is CI,
> the published test report and the last pass over the documentation.

## Quickstart

```bash
make up           # start Floci (pinned to 2.1.0)
make deploy       # build and push the images, apply the stack, migrate the database
make test         # unit tests
make integration  # pytest against the running emulator
make e2e          # Playwright against the deployed API
```

You need Docker, [uv](https://docs.astral.sh/uv/) and Node. Terraform runs in a pinned
container, so there is no Terraform to install.

The reasoning behind the technology choices is in [DECISIONS.md](DECISIONS.md).

## Trying it by hand

```bash
curl -s -X POST http://localhost:8088/transactions -H 'content-type: application/json' \
  -d '{"customer_id": "cust-1", "amount": "25000", "currency": "EUR", "country": "DE"}'
```

The answer comes back immediately with a transaction id and the status `pending`. A second
later the processor has had its say:

```bash
curl -s http://localhost:8088/transactions/<id>
```

Twenty five thousand euros is over the limit, so the transaction settles as rejected with
the rule that turned it down. The same answer is in the database:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
PGPASSWORD=$(aws secretsmanager get-secret-value --secret-id payments-db/master \
  --query SecretString --output text | jq -r .password) \
  psql -h localhost -p 7001 -U payments -d payments \
  -c "select transaction_id, status, decision_reason from transactions"
```

Put something that is not a transaction straight onto the queue and watch it arrive in
`payments-transactions-dlq` about a minute later.

The daily report runs at 02:00 on a schedule, which is a long time to wait, so ask for a
particular day instead:

```bash
aws lambda invoke --function-name payments-reporter --cli-binary-format raw-in-base64-out \
  --payload "{\"day\": \"$(date -u +%F)\"}" /dev/stdout
aws s3 cp "s3://payments-artifacts/reports/$(date -u +%F).csv" -
```

Port 8088 for an API that listens on 80, port 7001 for a database that thinks it is on
5432, and `localhost` where the secret says `floci`. All three are explained below.

## Where Floci differs from AWS

Floci is young, so before building anything on it I measured the seven things this
architecture depends on. Two of the answers changed the design.

| Question | Answer |
|---|---|
| Do returned URLs point somewhere reachable? | Only if you set `FLOCI_HOSTNAME`. |
| Does a zip Lambda run, and what endpoint does it see? | Yes, and `AWS_ENDPOINT_URL` is injected for you. |
| Is RDS a real PostgreSQL, and on which port? | Real `postgres:16.4`, on a proxy port, not 5432. |
| Can the API image be pushed to Floci's ECR? | Yes, straight from the host, no registry configuration. |
| Is an ECS task's port published on the host? | No, not when Floci itself runs in a container. |
| Does ELBv2 really route to ECS tasks? | Yes, including targets the ECS service registers itself. |
| Are IAM policies enforced? | For Lambda, genuinely. For ECS tasks, not at all. |

**RDS is not on 5432.** Floci runs a real `postgres:16-alpine` container and proxies to
it, and `DescribeDBInstances` returns a port out of the 7001 to 7099 range. So
`docker-compose.yml` publishes that whole range, `FLOCI_SERVICES_RDS_ENDPOINT_HOST` makes
the advertised address a name instead of a container IP, and host-side tests take the port
from the API and ignore the hostname.

**The ALB does route to ECS tasks, but its listener lives inside Floci.** This was the
open question, since Floci's ELBv2 documentation never mentions `ip` targets. Creating an
ECS service with a `loadBalancers` block registers the task address by itself and traffic
arrives. The listener binds a port *of the Floci container*, though, which is why compose
maps `8088:80` rather than publishing the task's own port. The load balancer's DNS name
does not resolve at all, so tests address the listener.

**IAM enforcement is real for Lambda and absent for ECS.** Floci ignores policies unless
`FLOCI_SERVICES_IAM_ENFORCEMENT_ENABLED` is set; with it on, a Lambda gets genuine
assumed-role credentials and a call outside its policy comes back `AccessDenied`. That is
what `tests/integration/test_least_privilege.py` leans on. ECS is the exception: vending
task-role credentials needs a helper image that is not published anywhere, and Floci falls
back to unrestricted credentials without a word in the logs. The task role is declared the
way it would be on AWS, but locally it constrains nothing, and this README would rather
say so than imply otherwise.

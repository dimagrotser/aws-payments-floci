# aws-payments-floci

A transaction processing system shaped the way you would actually build one on AWS: an API
on ECS writes to RDS and publishes to SQS, a Lambda applies anti-fraud rules and settles the
status, failed messages end up in a DLQ, and a scheduled Lambda drops a daily CSV on S3.
All of it is Terraform. None of it needs an AWS account, because it runs on
[Floci](https://floci.io), a local emulator.

> **Status: work in progress.** Stage 1 is done: transactions go into SQS, a Lambda
> applies the anti-fraud rules, decisions land in S3 and messages nobody can parse end up
> in the dead letter queue. RDS, the API on ECS and the daily report come next.

## Quickstart

```bash
make up           # start Floci (pinned to 2.1.0)
make deploy       # build the Lambda package and apply the Terraform stack
make test         # unit tests
make integration  # tests against the running emulator
```

You need Docker and [uv](https://docs.astral.sh/uv/). Terraform runs in a pinned
container, so there is no Terraform to install.

The reasoning behind the technology choices is in [DECISIONS.md](DECISIONS.md).

## Trying it by hand

```bash
QUEUE=$(jq -r .queue_url.value build/outputs.json)
export AWS_ENDPOINT_URL=http://localhost:4566 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test

aws sqs send-message --queue-url "$QUEUE" --message-body '{
  "transaction_id": "tx-1", "customer_id": "cust-1", "amount": "25000",
  "currency": "EUR", "country": "DE", "created_at": "2026-09-29T10:00:00+00:00"}'

aws s3api get-object --bucket payments-artifacts --key decisions/tx-1.json /dev/stdout
```

Twenty five thousand euros is over the limit, so the decision comes back rejected with the
rule that turned it down. Send something that is not JSON and watch it arrive in
`payments-transactions-dlq` about a minute later.

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

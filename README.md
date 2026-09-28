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

# aws-payments-floci

A transaction processing system shaped the way you would actually build one on AWS: an API
on ECS writes to RDS and publishes to SQS, a Lambda applies anti-fraud rules and settles the
status, failed messages end up in a DLQ, and a scheduled Lambda drops a daily CSV on S3.
All of it is Terraform. None of it needs an AWS account, because it runs on
[Floci](https://floci.io), a local emulator.

> **Status: work in progress.** Stage 0 is done: the environment, and a spike that checks
> what Floci actually does before anything gets built on top of it.

## Quickstart

```bash
make up     # start Floci (pinned to 2.1.0)
make help   # everything else
```

You need Docker. Terraform and the linters run in pinned containers, so there is nothing
else to install yet.

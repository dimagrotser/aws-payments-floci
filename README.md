# aws-payments-floci

An event-driven transaction processing system on AWS — API on ECS, anti-fraud in Lambda,
PostgreSQL on RDS, a daily CSV report on S3 — described entirely in Terraform and running
on your laptop against [Floci](https://floci.io), a free local AWS emulator. No AWS
account, no credentials, no bill.

> **Status: work in progress.** Stage 0 (environment + Floci spike) is done.
> See [docs/floci-notes.md](docs/floci-notes.md) for what was measured.

## Quickstart

```bash
make up     # start Floci (pinned 2.1.0)
make help   # everything else
```

Requires Docker. Terraform and the linters run in pinned containers.

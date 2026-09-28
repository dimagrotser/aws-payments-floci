import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";
import { Client } from "pg";
import { credentials, outputs } from "./outputs";

type Secret = {
  host: string;
  port: number;
  dbname: string;
  username: string;
  password: string;
};

export type TransactionRow = {
  transaction_id: string;
  customer_id: string;
  amount: string;
  status: string;
  decision_reason: string | null;
  processed_at: Date | null;
};

let cached: Promise<Client> | undefined;

async function connect(): Promise<Client> {
  const secrets = new SecretsManagerClient(credentials);
  const response = await secrets.send(
    new GetSecretValueCommand({ SecretId: outputs.db_secret_arn }),
  );
  const secret = JSON.parse(response.SecretString!) as Secret;

  // The port comes from the secret, the hostname does not: Floci advertises a name only
  // containers resolve, but it publishes that port on the host.
  const client = new Client({
    host: "localhost",
    port: secret.port,
    database: secret.dbname,
    user: secret.username,
    password: secret.password,
  });
  await client.connect();
  return client;
}

export function database(): Promise<Client> {
  cached ??= connect();
  return cached;
}

export async function closeDatabase(): Promise<void> {
  if (cached) {
    await (await cached).end();
    cached = undefined;
  }
}

export async function row(transactionId: string): Promise<TransactionRow | undefined> {
  const client = await database();
  const result = await client.query<TransactionRow>(
    "select transaction_id, customer_id, amount, status, decision_reason, processed_at" +
      " from transactions where transaction_id = $1",
    [transactionId],
  );
  return result.rows[0];
}

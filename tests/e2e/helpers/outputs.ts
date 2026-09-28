import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Outputs = {
  api_url: string;
  queue_url: string;
  dlq_url: string;
  db_secret_arn: string;
  max_receive_count: number;
};

const here = dirname(fileURLToPath(import.meta.url));
const path = resolve(here, "../../../build/outputs.json");

function read(): Outputs {
  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch {
    throw new Error(`${path} is missing. Run make up && make deploy first.`);
  }
  const parsed = JSON.parse(raw) as Record<string, { value: unknown }>;
  return Object.fromEntries(
    Object.entries(parsed).map(([key, entry]) => [key, entry.value]),
  ) as Outputs;
}

export const outputs = read();

// Floci hands out URLs containing a hostname only containers resolve, and the AWS SDK
// honours the queue URL rather than the endpoint. Rewriting is simpler than a DNS entry.
export const endpoint = process.env.AWS_ENDPOINT_URL ?? "http://localhost:4566";
export const fromHost = (url: string) => url.replace("http://floci:4566", endpoint);

export const credentials = {
  region: process.env.AWS_REGION ?? "us-east-1",
  endpoint,
  credentials: { accessKeyId: "test", secretAccessKey: "test" },
};

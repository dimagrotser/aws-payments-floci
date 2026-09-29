import { InvokeCommand, LambdaClient } from "@aws-sdk/client-lambda";
import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { credentials, outputs } from "./outputs";

const lambda = new LambdaClient(credentials);
const s3 = new S3Client({ ...credentials, forcePathStyle: true });

type ReportResult = { key: string; day: string; transactions: number };

// Floci offers no way to make a scheduled rule fire on demand, and waiting for 02:00 is
// not a test. The rule itself is asserted separately; here the reporter is invoked the
// way EventBridge would invoke it.
export async function runReport(day: string): Promise<ReportResult> {
  const response = await lambda.send(
    new InvokeCommand({
      FunctionName: outputs.reporter_function,
      Payload: Buffer.from(JSON.stringify({ day })),
    }),
  );
  if (response.FunctionError) {
    throw new Error(`reporter failed: ${Buffer.from(response.Payload!).toString()}`);
  }
  return JSON.parse(Buffer.from(response.Payload!).toString()) as ReportResult;
}

export async function readReport(key: string): Promise<Record<string, string>[]> {
  const response = await s3.send(
    new GetObjectCommand({ Bucket: outputs.bucket, Key: key }),
  );
  const body = await response.Body!.transformToString();
  const [header, ...lines] = body.trim().split("\n");
  const columns = header.split(",");
  return lines.map((line) =>
    Object.fromEntries(line.split(",").map((cell, index) => [columns[index], cell])),
  );
}

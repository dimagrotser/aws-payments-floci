import {
  DeleteMessageCommand,
  GetQueueAttributesCommand,
  ReceiveMessageCommand,
  SendMessageCommand,
  SQSClient,
} from "@aws-sdk/client-sqs";
import { credentials, fromHost, outputs } from "./outputs";

const sqs = new SQSClient(credentials);

export async function depth(queueUrl: string): Promise<number> {
  const response = await sqs.send(
    new GetQueueAttributesCommand({
      QueueUrl: fromHost(queueUrl),
      AttributeNames: ["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    }),
  );
  const attributes = response.Attributes ?? {};
  return (
    Number(attributes.ApproximateNumberOfMessages ?? 0) +
    Number(attributes.ApproximateNumberOfMessagesNotVisible ?? 0)
  );
}

export async function send(queueUrl: string, body: string): Promise<void> {
  await sqs.send(new SendMessageCommand({ QueueUrl: fromHost(queueUrl), MessageBody: body }));
}

export async function drain(queueUrl: string): Promise<string[]> {
  const bodies: string[] = [];
  for (;;) {
    const response = await sqs.send(
      new ReceiveMessageCommand({
        QueueUrl: fromHost(queueUrl),
        MaxNumberOfMessages: 10,
        WaitTimeSeconds: 0,
      }),
    );
    const messages = response.Messages ?? [];
    if (messages.length === 0) return bodies;
    for (const message of messages) {
      bodies.push(message.Body!);
      await sqs.send(
        new DeleteMessageCommand({
          QueueUrl: fromHost(queueUrl),
          ReceiptHandle: message.ReceiptHandle!,
        }),
      );
    }
  }
}

export const queues = { main: outputs.queue_url, dead: outputs.dlq_url };

import { expect, test } from "@playwright/test";
import { depth, drain, queues, send } from "../helpers/queues";

// The redrive is the slowest thing in the suite: three receives, each followed by the
// queue's visibility timeout.
test.describe.configure({ timeout: 180_000 });

test("a message the processor cannot parse ends up in the dead letter queue", async () => {
  await drain(queues.main);
  await drain(queues.dead);

  const poison = `not a transaction ${Date.now()}`;
  await send(queues.main, poison);

  await expect
    .poll(() => depth(queues.dead), { timeout: 150_000, intervals: [2_000] })
    .toBeGreaterThan(0);

  expect(await drain(queues.dead)).toContain(poison);
});

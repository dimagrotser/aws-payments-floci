import { APIRequestContext, expect, test } from "@playwright/test";
import { closeDatabase, row } from "../helpers/database";
import { depth, drain, queues } from "../helpers/queues";

type Submitted = { transaction_id: string; status: string };

test.afterAll(async () => {
  await closeDatabase();
});

async function submit(
  request: APIRequestContext,
  body: Record<string, unknown>,
): Promise<Submitted> {
  const response = await request.post("/transactions", { data: body });
  expect(response.status()).toBe(202);
  return (await response.json()) as Submitted;
}

test("an ordinary transaction is accepted and then approved", async ({ request }) => {
  const submitted = await submit(request, {
    customer_id: `cust-${Date.now()}`,
    amount: "120.00",
    currency: "EUR",
    country: "DE",
  });

  expect(submitted.status).toBe("pending");

  await expect
    .poll(
      async () => {
        const response = await request.get(`/transactions/${submitted.transaction_id}`);
        return ((await response.json()) as Submitted).status;
      },
      { message: "the processor should settle the transaction" },
    )
    .toBe("approved");

  // Same answer straight from the database, not through the API that wrote it.
  const settled = await row(submitted.transaction_id);
  expect(settled?.status).toBe("approved");
  expect(settled?.decision_reason).toBe("passed all rules");
  expect(settled?.processed_at).not.toBeNull();
});

test("a transaction over the limit is rejected with its reason", async ({ request }) => {
  const submitted = await submit(request, {
    customer_id: `cust-${Date.now()}`,
    amount: "50000.00",
    currency: "EUR",
    country: "DE",
  });

  await expect
    .poll(async () => (await row(submitted.transaction_id))?.status)
    .toBe("rejected");

  const settled = await row(submitted.transaction_id);
  expect(settled?.decision_reason).toContain("over limit");
});

test("a blocked country is rejected", async ({ request }) => {
  const submitted = await submit(request, {
    customer_id: `cust-${Date.now()}`,
    amount: "10.00",
    currency: "EUR",
    country: "KP",
  });

  await expect
    .poll(async () => (await row(submitted.transaction_id))?.status)
    .toBe("rejected");

  expect((await row(submitted.transaction_id))?.decision_reason).toContain("country KP is blocked");
});

test("the queue is empty once the work is done", async ({ request }) => {
  const submitted = await submit(request, {
    customer_id: `cust-${Date.now()}`,
    amount: "10.00",
    currency: "EUR",
    country: "DE",
  });

  await expect.poll(async () => (await row(submitted.transaction_id))?.status).toBe("approved");
  await expect.poll(async () => depth(queues.main)).toBe(0);
});

test("a nonexistent transaction is a 404", async ({ request }) => {
  const response = await request.get("/transactions/tx-never-existed");

  expect(response.status()).toBe(404);
});

test("the API refuses a transaction it cannot make sense of", async ({ request }) => {
  const response = await request.post("/transactions", {
    data: { customer_id: "c", amount: "-5", currency: "XXX", country: "Germany" },
  });

  expect(response.status()).toBe(422);
  const body = await response.text();
  expect(body).toContain("unsupported currency");
  expect(body).toContain("alpha-2");
});

test("nothing the API accepted ended up in the dead letter queue", async () => {
  expect(await drain(queues.dead)).toEqual([]);
});

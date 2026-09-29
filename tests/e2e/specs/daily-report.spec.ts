import { expect, test } from "@playwright/test";
import { closeDatabase, row } from "../helpers/database";
import { readReport, runReport } from "../helpers/reports";

test.afterAll(async () => {
  await closeDatabase();
});

test("a transaction settled today shows up in today's report", async ({ request }) => {
  const submission = await request.post("/transactions", {
    data: {
      customer_id: `cust-report-${Date.now()}`,
      amount: "77.00",
      currency: "EUR",
      country: "DE",
    },
  });
  expect(submission.status()).toBe(202);
  const { transaction_id } = (await submission.json()) as { transaction_id: string };

  await expect.poll(async () => (await row(transaction_id))?.status).toBe("approved");

  const today = new Date().toISOString().slice(0, 10);
  const result = await runReport(today);

  expect(result.key).toBe(`reports/${today}.csv`);

  const rows = await readReport(result.key);
  const reported = rows.find((entry) => entry.transaction_id === transaction_id);

  expect(reported).toBeDefined();
  expect(reported!.status).toBe("approved");
  expect(reported!.amount).toBe("77.00");
  expect(reported!.decision_reason).toBe("passed all rules");
});

test("a day nothing happened on still gets a report with only a header", async () => {
  const result = await runReport("2001-01-01");

  expect(result.transactions).toBe(0);
  expect(await readReport(result.key)).toEqual([]);
});

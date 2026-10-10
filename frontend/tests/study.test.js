import { test } from "node:test";
import assert from "node:assert/strict";
import { validatePages, sessionMarkdown, modes } from "../src/lib/study.js";
test("page scope rejects reversed, fractional and out-of-document ranges", () => {
  assert.equal(validatePages("", "", 3), null);
  assert.equal(validatePages("1", "3", 3), null);
  for (const [a, b] of [
    ["3", "1"],
    ["0", "2"],
    ["1.5", "2"],
    ["1", "4"],
  ])
    assert.ok(validatePages(a, b, 3));
});
test("study modes are distinct and exports preserve actual source page references", () => {
  assert.equal(new Set(modes.map((m) => m.id)).size, 5);
  const output = sessionMarkdown({ title: "Sample" }, [
    {
      query: "Q",
      response: {
        answer: "A",
        mode: "evidence",
        sources: [{ id: "S1", page: 7, text: "Real excerpt" }],
      },
    },
  ]);
  assert.match(output, /Page 7/);
  assert.match(output, /Real excerpt/);
  assert.match(output, /evidence/);
});

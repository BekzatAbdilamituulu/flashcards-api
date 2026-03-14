import test from "node:test";
import assert from "node:assert/strict";

import {
  collectSelectedCandidates,
  extractCandidatesFromHighlight,
  parseHighlightsWithCandidates,
} from "./highlightImport.js";

test("extracts word candidates from a simple sentence", () => {
  const candidates = extractCandidatesFromHighlight(
    "The protagonist felt serendipity in the dim library corridor."
  );
  const words = candidates.filter((c) => c.kind === "word").map((c) => c.text);
  assert.ok(words.includes("protagonist"));
  assert.ok(words.includes("serendipity"));
  assert.ok(words.includes("library"));
});

test("filters trivial tokens and stopwords", () => {
  const candidates = extractCandidatesFromHighlight("the and to in of an a");
  const words = candidates.filter((c) => c.kind === "word");
  assert.equal(words.length, 0);
});

test("collects only selected candidates for save", () => {
  const preview = [
    {
      text: "She whispered an enigmatic phrase.",
      sourcePage: "p. 11",
      sourceTitle: "Book A",
      candidates: [
        { text: "enigmatic", kind: "word", selected: true },
        { text: "enigmatic phrase", kind: "phrase", selected: false },
        { text: "She whispered an enigmatic phrase.", kind: "quote", selected: true },
      ],
    },
  ];
  const selected = collectSelectedCandidates(preview);
  assert.equal(selected.length, 2);
  assert.equal(selected[0].kind, "word");
  assert.equal(selected[1].kind, "quote");
  assert.equal(selected[0].sourcePage, "p. 11");
});

test("falls back to quote when no useful candidates", () => {
  const parsed = parseHighlightsWithCandidates("the and to in of an a");
  assert.equal(parsed.length, 1);
  const quote = parsed[0].candidates.find((c) => c.kind === "quote");
  assert.ok(quote);
  assert.equal(quote.selected, true);
});


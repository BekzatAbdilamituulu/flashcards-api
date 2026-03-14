const HIGHLIGHT_SPLIT_RE = /\n={3,}\n/g;

const STOPWORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "by",
  "for",
  "from",
  "had",
  "has",
  "have",
  "he",
  "her",
  "his",
  "i",
  "in",
  "is",
  "it",
  "its",
  "of",
  "on",
  "or",
  "our",
  "she",
  "that",
  "the",
  "their",
  "them",
  "they",
  "this",
  "to",
  "was",
  "we",
  "were",
  "with",
  "you",
  "your",
]);

function makeId(prefix, index) {
  return `${prefix}-${index}-${Math.random().toString(36).slice(2, 7)}`;
}

function normalizeToken(token) {
  return String(token || "")
    .toLowerCase()
    .replace(/^[^a-z0-9]+|[^a-z0-9]+$/gi, "")
    .trim();
}

function extractWordCandidates(text) {
  const tokens = String(text || "").split(/\s+/g).map(normalizeToken).filter(Boolean);
  const seen = new Set();
  const items = [];

  for (const token of tokens) {
    if (token.length < 3) continue;
    if (STOPWORDS.has(token)) continue;
    if (seen.has(token)) continue;
    seen.add(token);
    items.push(token);
    if (items.length >= 10) break;
  }

  return items;
}

function extractPhraseCandidates(text) {
  const rawTokens = String(text || "").split(/\s+/g).map(normalizeToken).filter(Boolean);
  const phrases = [];
  const seen = new Set();

  for (let i = 0; i < rawTokens.length - 1; i += 1) {
    const a = rawTokens[i];
    const b = rawTokens[i + 1];
    if (a.length < 3 || b.length < 3) continue;
    if (STOPWORDS.has(a) || STOPWORDS.has(b)) continue;
    const phrase = `${a} ${b}`;
    if (phrase.length > 32) continue;
    if (seen.has(phrase)) continue;
    seen.add(phrase);
    phrases.push(phrase);
    if (phrases.length >= 4) break;
  }

  return phrases;
}

export function extractCandidatesFromHighlight(text) {
  const clean = String(text || "").trim();
  if (!clean) return [];

  const words = extractWordCandidates(clean).map((token, idx) => ({
    id: makeId("word", idx),
    kind: "word",
    text: token,
    selected: idx < 3,
  }));

  const phrases = extractPhraseCandidates(clean).map((token, idx) => ({
    id: makeId("phrase", idx),
    kind: "phrase",
    text: token,
    selected: false,
  }));

  const quoteCandidate = {
    id: makeId("quote", 0),
    kind: "quote",
    text: clean,
    selected: false,
  };

  const candidates = [...words, ...phrases, quoteCandidate];
  const useful = candidates.some((c) => c.kind !== "quote");
  if (!useful) {
    quoteCandidate.selected = true;
  }
  return candidates;
}

function parseHighlightBlock(block, index) {
  const rawLines = String(block || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!rawLines.length) return null;

  let sourceTitle = "";
  let sourcePage = "";
  let metaLine = "";
  let textLines = [...rawLines];

  if (
    rawLines[0] &&
    rawLines[1] &&
    !/^[-•]\s*your\s+/i.test(rawLines[0]) &&
    /^[-•]\s*your\s+/i.test(rawLines[1])
  ) {
    sourceTitle = rawLines[0];
    textLines = rawLines.slice(1);
  }

  if (textLines[0] && /^[-•]\s*your\s+/i.test(textLines[0])) {
    metaLine = textLines[0];
    textLines = textLines.slice(1);
  }

  const pageMatch = metaLine.match(/\bpage\s+(\d+)\b/i);
  if (pageMatch) sourcePage = `p. ${pageMatch[1]}`;
  const locMatch = metaLine.match(/\blocation\s+([0-9\-]+)\b/i);
  if (!sourcePage && locMatch) sourcePage = `loc ${locMatch[1]}`;

  const text = textLines.join(" ").trim();
  if (!text) return null;

  return {
    id: makeId("highlight", index),
    sourceTitle,
    sourcePage,
    text,
    candidates: extractCandidatesFromHighlight(text),
  };
}

export function parseHighlightsWithCandidates(rawText) {
  const normalized = String(rawText || "").replace(/\r\n/g, "\n").trim();
  if (!normalized) return [];

  const hasKindleDelimiters = normalized.includes("==========");
  const blocks = hasKindleDelimiters
    ? normalized.split(HIGHLIGHT_SPLIT_RE)
    : normalized
        .split(/\n{2,}/g)
        .map((chunk) => chunk.trim())
        .filter(Boolean);

  const parsed = blocks.map((block, idx) => parseHighlightBlock(block, idx)).filter(Boolean);
  if (parsed.length) return parsed;

  return normalized
    .split("\n")
    .map((line, idx) => parseHighlightBlock(line, idx))
    .filter(Boolean);
}

export function collectSelectedCandidates(previewItems) {
  const items = Array.isArray(previewItems) ? previewItems : [];
  const out = [];
  for (const item of items) {
    for (const candidate of item.candidates || []) {
      if (!candidate?.selected) continue;
      const text = String(candidate?.text || "").trim();
      if (!text) continue;
      out.push({
        text,
        kind: candidate.kind || "quote",
        sourceSentence: item.text || "",
        sourcePage: item.sourcePage || "",
        sourceTitle: item.sourceTitle || "",
      });
    }
  }
  return out;
}

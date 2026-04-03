import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { DecksApi, ReadingSourcesApi, StudyApi } from "../api/endpoints";
import Button from "../components/Button";
import Card from "../components/Card";
import { useActivePair } from "../context/ActivePairContext";
import { memoryStrengthFromCard } from "../utils/memoryStrength";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildClozeSentence(sentence, word) {
  const sourceSentence = String(sentence || "").trim();
  const sourceWord = String(word || "").trim();
  if (!sourceSentence || !sourceWord) return null;

  const safeWord = escapeRegExp(sourceWord);
  const regex = new RegExp(`\\b${safeWord}\\b`, "gi");
  const maskedByBoundary = sourceSentence.replace(regex, "______");
  if (maskedByBoundary !== sourceSentence) return maskedByBoundary;

  const plainRegex = new RegExp(safeWord, "gi");
  const maskedByPlain = sourceSentence.replace(plainRegex, "______");
  if (maskedByPlain !== sourceSentence) return maskedByPlain;

  return null;
}

function renderSentenceWithEmphasis(sentence, word, className) {
  const sourceSentence = String(sentence || "").trim();
  const sourceWord = String(word || "").trim();
  if (!sourceSentence) return null;
  if (!sourceWord) return <span className={className}>{sourceSentence}</span>;

  const safeWord = escapeRegExp(sourceWord);
  const regex = new RegExp(`(${safeWord})`, "gi");
  const parts = sourceSentence.split(regex);

  return (
    <span className={className}>
      {parts.map((part, index) => {
        const matchesWord = part && part.localeCompare(sourceWord, undefined, { sensitivity: "accent" }) === 0;
        if (!matchesWord && part.toLowerCase() !== sourceWord.toLowerCase()) {
          return <span key={`${part}-${index}`}>{part}</span>;
        }
        return (
          <mark key={`${part}-${index}`} className="rounded bg-indigo-100 px-1 text-inherit">
            {part}
          </mark>
        );
      })}
    </span>
  );
}

function formatLocalDateTime(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

export default function StudyPage() {
  const { deckId } = useParams();
  const id = Number(deckId);
  const sourceId = Number(new URLSearchParams(window.location.search).get("sourceId") || 0);
  const { activePair } = useActivePair();

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [deckName, setDeckName] = useState("");
  const [deckMeta, setDeckMeta] = useState(null);
  const [sourceMeta, setSourceMeta] = useState(null);

  const [batch, setBatch] = useState(null);
  const [idx, setIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);

  const current = useMemo(() => batch?.cards?.[idx] ?? null, [batch, idx]);
  const clozeSentence = useMemo(
    () => buildClozeSentence(current?.source_sentence, current?.front),
    [current]
  );
  const isClozeMode = Boolean(clozeSentence);
  const reviewSourceTitle = current?.reading_source?.title || current?.source_title || sourceMeta?.title || deckName || `Source #${id}`;
  const reviewSourceAuthor = current?.reading_source?.author || current?.source_author || sourceMeta?.author || deckMeta?.author_name || null;
  const reviewSentence = current?.source_sentence || current?.example_sentence || null;
  const savedAtLabel = formatLocalDateTime(current?.created_at);
  const memoryStrength = memoryStrengthFromCard(current);
  const sourceContextLabel = sourceMeta?.kind || current?.source_kind || "Book";
  const remaining = useMemo(() => {
    if (!batch?.cards?.length) return 0;
    return Math.max(0, batch.cards.length - idx - 1);
  }, [batch, idx]);

  async function loadBatch() {
    setLoading(true);
    setError("");
    setBatch(null);
    setIdx(0);
    setRevealed(false);

    try {
      const res = await StudyApi.next(id, sourceId > 0 ? { reading_source_id: sourceId } : {});
      setBatch(res.data);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  async function answer(learned) {
    if (!current) return;
    setBusy(true);
    setError("");

    try {
      await StudyApi.answer(current.id, learned);

      const nextIndex = idx + 1;
      if (batch && nextIndex < batch.cards.length) {
        setIdx(nextIndex);
        setRevealed(false);
      } else {
        await loadBatch();
      }
    } catch (e) {
      setError(extractError(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    async function loadDeck() {
      if (!activePair?.id) {
        setDeckName("");
        setError("No active learning pair selected.");
        setLoading(false);
        return;
      }

      try {
        const requests = [DecksApi.list(200, 0, { pair_id: activePair.id })];
        if (sourceId > 0) requests.push(ReadingSourcesApi.get(sourceId));

        const [decksRes, sourceRes] = await Promise.all(requests);
        const pairDecks = decksRes.data?.items ?? [];
        const match = pairDecks.find((deck) => Number(deck.id) === id) ?? null;

        if (!match) {
          setDeckName("");
          setDeckMeta(null);
          setSourceMeta(null);
          setError("This review is not available for the active pair.");
          setLoading(false);
          return;
        }

        setDeckName(match.name || "");
        setDeckMeta(match);
        setSourceMeta(sourceRes?.data ?? null);
      } catch (e) {
        setDeckName("");
        setDeckMeta(null);
        setSourceMeta(null);
        setError(extractError(e));
        setLoading(false);
        return;
      }

      await loadBatch();
    }

    if (id > 0) {
      loadDeck();
    } else {
      setError("Invalid review id.");
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, sourceId, activePair?.id]);

  return (
    <div className="mx-auto w-full max-w-md space-y-4 pb-8 pt-2">
      <div className="rounded-3xl border border-white/50 bg-gradient-to-br from-indigo-500/20 via-blue-600/15 to-purple-600/20 p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="rounded-2xl bg-white/80 px-3 py-2 text-left shadow-sm">
            <p className="text-[11px] uppercase tracking-[0.24em] text-indigo-700/60">Reading memory</p>
            <p className="text-sm font-semibold text-gray-900">{sourceContextLabel}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-indigo-700/60">Reviewing from</p>
            <p className="text-sm font-semibold text-gray-900">{reviewSourceTitle}</p>
            {reviewSourceAuthor ? (
              <p className="text-xs text-indigo-700/60">{reviewSourceAuthor}</p>
            ) : null}
          </div>
          <div className="rounded-2xl bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm">
            {idx + 1} / {batch?.cards?.length ?? 0}
          </div>
        </div>
      </div>

      {loading ? <p className="text-center text-sm text-gray-500">Loading entries...</p> : null}

      {error ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
      ) : null}

      {!loading && current ? (
        <div className="space-y-5">
          <div className="relative mx-3 mt-2">
            <div className="pointer-events-none absolute inset-x-3 top-3 h-full rounded-3xl border border-indigo-100/60 bg-indigo-50/50" />
            <div className="pointer-events-none absolute inset-x-1 top-1 h-full rounded-3xl border border-indigo-100/60 bg-indigo-100/30" />
            <Card className="relative rounded-2xl px-6 py-8 text-center">
              <div className="mb-6 flex flex-wrap items-center justify-center gap-2 text-[11px] uppercase tracking-[0.22em] text-indigo-700/60">
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-indigo-700">Reading review</span>
                {current.source_page ? (
                  <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-900">
                    Page {current.source_page}
                  </span>
                ) : null}
              </div>
              <div className="flex min-h-[220px] items-center justify-center">
                {!revealed ? (
                  <div className="space-y-4">
                    {isClozeMode ? (
                      <p className="text-2xl font-semibold leading-relaxed text-gray-900">
                        {clozeSentence.split("______").map((part, index, arr) => (
                          <span key={`${index}-${part}`}>
                            {part}
                            {index < arr.length - 1 ? (
                              <span className="mx-1 rounded bg-indigo-200 px-2 py-0.5 font-bold tracking-wide">
                                ______
                              </span>
                            ) : null}
                          </span>
                        ))}
                      </p>
                    ) : (
                      <>
                        <p className="text-xs uppercase tracking-[0.24em] text-indigo-700/60">Word to remember</p>
                        <p className="text-4xl font-bold leading-tight text-gray-900">{current.front}</p>
                      </>
                    )}
                    {reviewSentence ? (
                      <div className="space-y-2 rounded-3xl border border-indigo-100/60 bg-indigo-50/30 px-4 py-4 text-left">
                        <p className="text-xs uppercase tracking-[0.24em] text-indigo-700/60">
                          {isClozeMode ? "Fill the blank from the sentence" : "Seen in the book"}
                        </p>
                        {renderSentenceWithEmphasis(reviewSentence, current.front, "text-base leading-relaxed text-gray-800")}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <p className="text-xs uppercase tracking-[0.24em] text-indigo-700/60">Word</p>
                      <p className="text-3xl font-bold leading-tight text-gray-900">{current.front}</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-xs uppercase tracking-[0.24em] text-indigo-700/60">Meaning</p>
                      <p className="text-2xl font-semibold leading-tight text-gray-900">{current.back}</p>
                    </div>
                    {reviewSentence ? (
                      <div className="space-y-2 rounded-3xl border border-indigo-100/60 bg-indigo-50/30 px-4 py-4 text-left">
                        <p className="text-xs uppercase tracking-[0.24em] text-indigo-700/60">Sentence from the book</p>
                        {renderSentenceWithEmphasis(reviewSentence, current.front, "text-lg leading-relaxed text-gray-900")}
                      </div>
                    ) : null}
                    <div className="grid gap-2 text-left text-sm text-gray-600">
                      <p>Memory strength: {memoryStrength}</p>
                      {reviewSourceTitle ? (
                        <p>
                          Source: {reviewSourceTitle}
                          {reviewSourceAuthor ? ` · ${reviewSourceAuthor}` : ""}
                        </p>
                      ) : null}
                      {current.source_page ? <p>Page: {current.source_page}</p> : null}
                      {savedAtLabel ? <p>Saved: {savedAtLabel}</p> : null}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>

          {!revealed ? (
            <Button variant="primary" onClick={() => setRevealed(true)} disabled={busy} className="w-full">
              Reveal Answer
            </Button>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <Button variant="secondary" onClick={() => answer(false)} disabled={busy} className="w-full">
                I don't know
              </Button>
              <Button variant="primary" onClick={() => answer(true)} disabled={busy} className="w-full">
                I know
              </Button>
            </div>
          )}

          <p className="text-center text-xs text-gray-500">Remaining in this batch: {remaining}</p>
        </div>
      ) : null}

      {!loading && !current && !error ? (
        <Card className="text-center">
          <h2 className="text-lg font-semibold">No reviewable entries</h2>
          <p className="mt-1 text-gray-700">No entries available for this source in the active pair.</p>
          <Button className="mt-4 w-full" variant="primary" onClick={loadBatch}>
            Load next batch
          </Button>
        </Card>
      ) : null}
    </div>
  );
}

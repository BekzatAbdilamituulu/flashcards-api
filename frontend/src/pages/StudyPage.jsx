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
          setError("This study deck is not available for the active pair.");
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
      setError("Invalid study deck id.");
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, sourceId, activePair?.id]);

  return (
    <div className="mx-auto w-full max-w-md space-y-4 pb-8">
      <div className="rounded-xl border border-gray-200 bg-white p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="h-11 w-11" />
          <div className="text-center">
            <p className="text-xs text-gray-500">Reading review</p>
            <p className="text-sm font-medium text-gray-900">{reviewSourceTitle}</p>
            {reviewSourceAuthor ? (
              <p className="text-xs text-gray-500">{reviewSourceAuthor}</p>
            ) : null}
          </div>
          <div className="rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700">
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
            <div className="pointer-events-none absolute inset-x-3 top-3 h-full rounded-2xl border border-gray-200 bg-gray-50" />
            <div className="pointer-events-none absolute inset-x-1 top-1 h-full rounded-2xl border border-gray-200 bg-gray-100" />
            <Card className="relative rounded-2xl px-6 py-8 text-center shadow-sm">
              <div className="flex min-h-[220px] items-center justify-center">
                {!revealed ? (
                  <div className="space-y-4">
                    {isClozeMode ? (
                      <p className="text-2xl font-semibold leading-relaxed text-black">
                        {clozeSentence.split("______").map((part, index, arr) => (
                          <span key={`${index}-${part}`}>
                            {part}
                            {index < arr.length - 1 ? (
                              <span className="mx-1 rounded bg-gray-200 px-2 py-0.5 font-bold tracking-wide">
                                ______
                              </span>
                            ) : null}
                          </span>
                        ))}
                      </p>
                    ) : (
                      <p className="text-4xl font-bold leading-tight text-black">{current.front}</p>
                    )}
                    {reviewSentence ? (
                      <p className="text-sm text-gray-500">
                        {isClozeMode ? "Fill the blank from context." : `Source sentence: ${reviewSentence}`}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {isClozeMode ? (
                      <>
                        <p className="text-xs uppercase tracking-wide text-gray-500">Context</p>
                        <p className="text-lg leading-relaxed text-black">{reviewSentence}</p>
                      </>
                    ) : (
                      <>
                        <p className="text-xs uppercase tracking-wide text-gray-500">Word</p>
                        <p className="text-3xl font-bold leading-tight text-black">{current.front}</p>
                      </>
                    )}
                    <p className="text-xs uppercase tracking-wide text-gray-500">
                      {isClozeMode ? "Word" : "Meaning"}
                    </p>
                    <p className="text-2xl font-semibold leading-tight text-gray-900">
                      {isClozeMode ? current.front : current.back}
                    </p>
                    <p className="text-xs uppercase tracking-wide text-gray-500">Meaning</p>
                    <p className="text-2xl font-semibold leading-tight text-gray-900">{current.back}</p>
                    {current.source_page ? (
                      <p className="text-sm text-gray-600">Source page: {current.source_page}</p>
                    ) : null}
                    {reviewSentence ? (
                      <p className="text-sm text-gray-600">Source sentence: {reviewSentence}</p>
                    ) : null}
                    <p className="text-sm text-gray-600">Memory strength: {memoryStrength}</p>
                    {reviewSourceTitle ? (
                      <p className="text-sm text-gray-600">
                        Source: {reviewSourceTitle}
                        {reviewSourceAuthor ? ` · ${reviewSourceAuthor}` : ""}
                      </p>
                    ) : null}
                    {savedAtLabel ? (
                      <p className="text-sm text-gray-600">Saved: {savedAtLabel}</p>
                    ) : null}
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
